/**
 * Shared evaluator logic for the Sysadmin Competency Assessment Platform.
 * This module is designed to be usable in both Browser (Vite/React) and Node.js environments.
 */

/**
 * Assemble the evaluator system prompt from a scenario definition.
 * Handles Mode A (artifact analysis) and Mode B (document production).
 * Optionally extends with coach mode instructions.
 */
export function buildSystemPrompt(scenario, artifactContent, { coachMode = false, coachRound = 0, compactRubric = false } = {}) {
  const { schema_version = 1.0, domain_name, level, title, delivery_mode, delivery_modes, presentation, rubric } = scenario

  // Handle schema V2 delivery_modes array or V1 delivery_mode string
  const mode = delivery_mode || (delivery_modes && delivery_modes[0]) || 'A'

  // Resolve presentation context/type based on schema version
  const activePresentation = (schema_version >= 2.0 && presentation.modes) 
    ? (presentation.modes[mode] || presentation.modes['A'] || {}) 
    : presentation

  const presentationType = activePresentation.type || 'text'
  const presentationContext = activePresentation.context || ''

  let criticalBlock = ''
  let secondaryBlock = ''

  // Logic: miss_signal is diagnostic guidance for the AI (included by default).
  // learning_note is the "revealed truth" for the learner and is EXCLUDED to 
  // prevent the AI from leaking the correct answer in the narrative.
  const formatFinding = (f) => {
    let block = `[${f.id}] (Severity: ${f.type || f.severity}) ${f.description.trim()}`
    if (!compactRubric && f.miss_signal) {
      block += `\nWATCH FOR (MISS SIGNAL): ${f.miss_signal.trim()}`
    }
    return block
  }

  if (schema_version >= 2.0 && rubric.findings) {
    criticalBlock = rubric.findings
      .filter(f => f.type === 'critical')
      .map(formatFinding)
      .join('\n\n')
    
    secondaryBlock = rubric.findings
      .filter(f => f.type === 'secondary')
      .map(formatFinding)
      .join('\n\n')
  } else {
    criticalBlock = (rubric.critical_findings ?? []).map(formatFinding).join('\n\n')
    secondaryBlock = (rubric.secondary_findings ?? []).map(formatFinding).join('\n\n')
  }

  const levelBlock = Object.entries(rubric.level_indicators ?? {}).map(([k, v]) =>
    `${k.replace('level_', 'Level ')}: ${v.trim()}`
  ).join('\n\n')

  const modeNote = mode === 'B'
    ? `This is a Commission exercise (Mode B). The candidate has been asked to produce a specification or document — not to analyse a given artifact. Evaluate the completeness and quality of what they produced against the rubric findings, which represent required elements of a correct specification.`
    : `This is an Audit/Literacy exercise (Mode ${mode}). The candidate has been asked to analyse the provided artifact and identify findings.`

  // Optional coach mode fields appended to JSON schema
  let coachJsonFields = ''
  let coachInstructions = ''

  if (coachMode) {
    if (coachRound === 0) {
      coachJsonFields = `,\n  "coach_question": <string — a single Socratic question pointing to specific artifact evidence for the primary missed finding; omit this field entirely if all findings are caught>`
      coachInstructions = `\n\nCOACH MODE: After evaluating, if any findings were missed, include a "coach_question" field — a single Socratic question pointing to specific evidence in the artifact that would help the candidate discover their primary missed finding. Do not name the finding or reveal the correct answer. The question should be answerable from the artifact alone. Omit this field if no findings were missed.`
    } else {
      coachJsonFields = `,\n  "resolved": <true|false — whether the candidate has now identified the primary missed finding>,\n  "coach_question": <string — a more direct follow-up question; omit if resolved is true or if round >= 3>`
      coachInstructions = `\n\nFOLLOW-UP COACHING (round ${coachRound} of 3): The candidate has responded to a coaching question. The exchange history follows the initial response in the message thread. Determine whether they have now identified the primary missed finding:\n- If yes: set "resolved": true and complete all evaluation fields normally.\n- If no and round < 3: set "resolved": false and include a more direct "coach_question".\n- If no and round >= 3: set "resolved": false and omit "coach_question" — the UI will surface explanation content for the candidate.`
    }
  }

  return `ROLE: You are an assessment evaluator for the Modern Systems Administration Competency Framework. You are evaluating a candidate's response to a scenario exercise. Do not provide the correct answer or reveal findings the candidate missed.

${modeNote}

DOMAIN: ${domain_name} (Level ${level})
EXERCISE: ${title}

SCENARIO CONTEXT:
${presentationContext.trim()}

${artifactContent ? `ARTIFACT (${presentationType}):\n\`\`\`\n${artifactContent}\n\`\`\`` : '(No artifact — Mode B commission exercise)'}

RUBRIC

Critical findings:
${criticalBlock || 'None'}

Secondary findings:
${secondaryBlock || 'None'}

Level indicators:
${levelBlock || 'Not specified'}

EVALUATION INSTRUCTIONS:
1. Assess the candidate's response against the rubric.
2. Identify which finding IDs were caught (clearly addressed) and which were missed.
3. Assess severity calibration — did they rate critical findings as critical?
4. Credit legitimate findings not in the rubric (note them as "unlisted_N").
5. Produce a level estimate (1–4) with specific evidence from the response.
6. If the candidate is between levels, describe the specific gap.
7. Do NOT reveal what was missed or provide the correct answer.

Respond with a single JSON object — no prose before or after it:
{
  "level": <1|2|3|4>,
  "confidence": <"high"|"medium"|"low">,
  "caught": [<finding id strings>],
  "missed": [<finding id strings>],
  "almost_caught": [<finding id strings — findings that the candidate touched on or mentioned but did not describe with enough precision to be fully credited according to the rubric>],
  "unlisted": [<brief descriptions of valid unlisted findings>],
  "severity_calibration": <"accurate"|"understated"|"overstated"|"mixed">,
  "gap": <"prose description of what separates this response from the next level, or null if clearly at a level">,
  "narrative": <"1–2 paragraph assessment of the response, suitable for the candidate to read. Do not reveal missed findings or the correct answer.">${coachJsonFields}
}${coachInstructions}`
}

/**
 * Perform an evaluation using an OpenAI-compatible client.
 */
export async function performEvaluation({ 
  client, 
  model, 
  scenario, 
  artifactContent, 
  responseText, 
  coachMode = false, 
  coachRound = 0, 
  coachHistory = [], 
  compactRubric = false,
  isRetry = false 
}) {
  const systemPrompt = buildSystemPrompt(scenario, artifactContent, { coachMode, coachRound, compactRubric })

  const messages = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: responseText },
    ...coachHistory,
  ]

  const response = await client.chat.completions.create({
    model: model,
    max_tokens: 2048,
    messages,
  })

  const raw = response.choices[0]?.message?.content ?? ''

  // Extract JSON — model may wrap it in a code block
  const jsonMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/) ?? raw.match(/(\{[\s\S]*\})/)
  const jsonStr = jsonMatch ? (jsonMatch[1] ?? jsonMatch[0]) : raw

  let parsed = null
  try {
    parsed = JSON.parse(jsonStr.trim())
  } catch (err) {
    if (!isRetry) {
      return performEvaluation({ 
        client, 
        model, 
        scenario, 
        artifactContent, 
        responseText, 
        coachMode, 
        coachRound, 
        coachHistory, 
        compactRubric,
        isRetry: true 
      })
    }
    return { raw, parsed: null, error: 'JSON parse failure after retry' }
  }

  return { raw, parsed }
}
