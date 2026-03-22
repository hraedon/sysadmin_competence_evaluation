import OpenAI from 'openai'

// ---------------------------------------------------------------------------
// Settings schema and persistence
// ---------------------------------------------------------------------------

export const SETTINGS_KEY = 'sysadmin_assessment_settings'
const LEGACY_KEY = 'sysadmin_assessment_api_key'

export const DEFAULT_SETTINGS = {
  provider: 'local',
  endpoint: 'http://192.168.1.28:1234/v1',
  apiKey: '',
  model: 'qwen3-next-80b-a3b-instruct-mlx',
  evaluatorMode: 'auditor',
}

/** Load settings from localStorage, migrating the legacy API key if present. */
export function loadSettings() {
  const stored = localStorage.getItem(SETTINGS_KEY)
  if (stored) {
    try {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) }
    } catch {
      // fall through to defaults
    }
  }
  // Migrate legacy Anthropic-only key
  const legacyKey = localStorage.getItem(LEGACY_KEY)
  if (legacyKey) {
    const migrated = { ...DEFAULT_SETTINGS, provider: 'anthropic', apiKey: legacyKey }
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(migrated))
    localStorage.removeItem(LEGACY_KEY)
    return migrated
  }
  return { ...DEFAULT_SETTINGS }
}

/** Persist settings to localStorage. */
export function saveSettings(settings) {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings))
}

// ---------------------------------------------------------------------------
// Provider abstraction
// ---------------------------------------------------------------------------

const PROVIDER_BASE_URLS = {
  local:     null,                             // uses settings.endpoint
  anthropic: 'https://api.anthropic.com/v1',
  openai:    'https://api.openai.com/v1',
  custom:    null,                             // uses settings.endpoint
}

/**
 * Build an OpenAI-compatible client for the given provider settings.
 * All providers (including Anthropic) are accessed via the openai package
 * using their OpenAI-compatible endpoints.
 */
export function buildClient({ provider = 'local', endpoint, apiKey }) {
  const baseURL = PROVIDER_BASE_URLS[provider] ?? endpoint ?? 'http://192.168.1.28:1234/v1'
  // Local providers don't require a real key; use a placeholder so the header is valid
  const key = apiKey || (provider === 'local' ? 'lm-studio' : 'no-key')
  return new OpenAI({ baseURL, apiKey: key, dangerouslyAllowBrowser: true })
}

// ---------------------------------------------------------------------------
// Prompt assembly
// ---------------------------------------------------------------------------

/**
 * Assemble the evaluator system prompt from a scenario definition.
 * Handles Mode A (artifact analysis) and Mode B (document production).
 * Optionally extends with coach mode instructions.
 */
function buildSystemPrompt(scenario, artifactContent, { coachMode = false, coachRound = 0 } = {}) {
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
  "narrative": <"1–2 paragraph assessment of the response, suitable for the candidate to read. Do not reveal missed findings or the correct answer.">${coachJsonFields}
}${coachInstructions}`
}

// ---------------------------------------------------------------------------
// Evaluator
// ---------------------------------------------------------------------------

/**
 * Call the configured provider and return a parsed evaluation result.
 *
 * In coach mode, coachRound and coachHistory extend the conversation:
 *   coachRound 0 = initial evaluation (coach_question added to JSON if findings missed)
 *   coachRound 1+ = follow-up (coachHistory contains prior exchanges, resolved field added)
 *
 * coachHistory is an array of { role: 'assistant'|'user', content } messages
 * representing exchanges after the initial response.
 *
 * Throws on API/network error. Returns { raw, parsed } where parsed may be
 * null if JSON extraction fails.
 */
export async function evaluate({ scenario, artifactContent, responseText, settings, coachMode = false, coachRound = 0, coachHistory = [] }) {
  const client = buildClient(settings)
  const systemPrompt = buildSystemPrompt(scenario, artifactContent, { coachMode, coachRound })

  const messages = [
    { role: 'system', content: systemPrompt },
    { role: 'user', content: responseText },
    ...coachHistory,
  ]

  const response = await client.chat.completions.create({
    model: settings.model,
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
  } catch {
    // Fallback: return raw text, let UI show it
  }

  return { raw, parsed }
}
