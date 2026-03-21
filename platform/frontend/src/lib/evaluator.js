import Anthropic from '@anthropic-ai/sdk'

/**
 * Assemble the evaluator system prompt from a scenario definition.
 * Handles Mode A (artifact analysis) and Mode B (document production).
 */
function buildSystemPrompt(scenario, artifactContent) {
  const { domain_name, level, title, delivery_mode, presentation, rubric } = scenario

  const criticalBlock = (rubric.critical_findings ?? []).map(f =>
    `[${f.id}] ${f.description.trim()}\n  Severity: ${f.severity}\n  Miss signal: ${(f.miss_signal ?? '').trim()}`
  ).join('\n\n')

  const secondaryBlock = (rubric.secondary_findings ?? []).map(f =>
    `[${f.id}] ${f.description.trim()}\n  Severity: ${f.severity}`
  ).join('\n\n')

  const levelBlock = Object.entries(rubric.level_indicators ?? {}).map(([k, v]) =>
    `${k.replace('level_', 'Level ')}: ${v.trim()}`
  ).join('\n\n')

  const modeNote = delivery_mode === 'B'
    ? `This is a Commission exercise (Mode B). The candidate has been asked to produce a specification or document — not to analyse a given artifact. Evaluate the completeness and quality of what they produced against the rubric findings, which represent required elements of a correct specification.`
    : `This is an Audit/Literacy exercise (Mode ${delivery_mode}). The candidate has been asked to analyse the provided artifact and identify findings.`

  const artifactSection = artifactContent
    ? `ARTIFACT (${presentation.type}):\n\`\`\`\n${artifactContent}\n\`\`\``
    : '(No artifact — Mode B commission exercise)'

  return `ROLE: You are an assessment evaluator for the Modern Systems Administration Competency Framework. You are evaluating a candidate's response to a scenario exercise. Do not provide the correct answer or reveal findings the candidate missed.

${modeNote}

DOMAIN: ${domain_name} (Level ${level})
EXERCISE: ${title}

SCENARIO CONTEXT:
${presentation.context?.trim() ?? ''}

${artifactSection}

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
  "unlisted": [<brief descriptions of valid unlisted findings>],
  "severity_calibration": <"accurate"|"understated"|"overstated"|"mixed">,
  "gap": <"prose description of what separates this response from the next level, or null if clearly at a level">,
  "narrative": <"1–2 paragraph assessment of the response, suitable for the candidate to read. Do not reveal missed findings or the correct answer.">
}`
}

/**
 * Call the Anthropic API and return a parsed evaluation result.
 * Throws on API error. Returns { raw, parsed } where parsed may be null if
 * JSON extraction fails.
 */
export async function evaluate({ scenario, artifactContent, responseText, apiKey, model = 'claude-sonnet-4-6' }) {
  const client = new Anthropic({ apiKey, dangerouslyAllowBrowser: true })

  const systemPrompt = buildSystemPrompt(scenario, artifactContent)

  const message = await client.messages.create({
    model,
    max_tokens: 2048,
    system: systemPrompt,
    messages: [{ role: 'user', content: responseText }],
  })

  const raw = message.content[0]?.text ?? ''

  // Extract JSON — model may wrap it in a code block
  const jsonMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/) ?? raw.match(/(\{[\s\S]*\})/)
  const jsonStr = jsonMatch ? (jsonMatch[1] ?? jsonMatch[0]) : raw

  let parsed = null
  try {
    parsed = JSON.parse(jsonStr.trim())
  } catch {
    // Fallback: return raw text, let UI show it
  }

  return { raw, parsed }
}
