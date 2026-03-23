#!/usr/bin/env node
/**
 * Calibration harness for the sysadmin competency assessment evaluator.
 *
 * Supports multiple providers via CLI flags:
 *
 *   # Local (default — no key required):
 *   node run.mjs
 *   node run.mjs --provider local --endpoint http://192.168.1.28:1234/v1 --model qwen3-next-80b-a3b-instruct-mlx
 *
 *   # Anthropic:
 *   ANTHROPIC_API_KEY=sk-ant-... node run.mjs --provider anthropic
 *   ANTHROPIC_API_KEY=sk-ant-... node run.mjs --provider anthropic --model claude-opus-4-6
 *
 *   # OpenAI:
 *   OPENAI_API_KEY=sk-... node run.mjs --provider openai --model gpt-4o
 *
 *   # Custom endpoint:
 *   node run.mjs --provider custom --endpoint http://my-server:8080/v1 --model my-model
 *   node run.mjs --provider custom --endpoint http://my-server:8080/v1 --api-key mykey --model my-model
 *
 * Filters:
 *   --scenario d01-audit-ai-gave-you-this
 *   --domain 1
 *
 * Exit codes:
 *   0 — all calibrated scenarios passed (level match within tolerance)
 *   1 — one or more scenarios failed calibration
 *   2 — configuration error (no scenarios found, missing required key, etc.)
 */

import OpenAI from 'openai'
import { readFileSync, existsSync, writeFileSync, mkdirSync } from 'fs'
import { join, dirname, resolve } from 'path'
import { fileURLToPath } from 'url'
import { load as parseYaml } from 'js-yaml'
import { glob } from 'glob'

const __dirname = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(__dirname, '..')
const SCENARIOS_DIR = join(REPO_ROOT, 'scenarios')
const RESULTS_DIR = join(__dirname, 'results')
const EXPECTED_LEVELS = [1, 2, 3, 4]
const PASS_TOLERANCE = 0.5

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------

const args = process.argv.slice(2)

function getArg(flag, defaultValue = null) {
  const i = args.indexOf(flag)
  return i !== -1 ? args[i + 1] : defaultValue
}

const scenarioFilter = getArg('--scenario')
const domainFilter   = getArg('--domain') ? parseInt(getArg('--domain')) : null
const providerFlag   = getArg('--provider', 'local')
const endpointFlag   = getArg('--endpoint')
const modelFlag      = getArg('--model')
const apiKeyFlag     = getArg('--api-key')

// ---------------------------------------------------------------------------
// Provider configuration
// ---------------------------------------------------------------------------

const PROVIDER_DEFAULTS = {
  local:     { baseURL: 'http://192.168.1.28:1234/v1', model: 'qwen3-next-80b-a3b-instruct-mlx', requiresKey: false },
  anthropic: { baseURL: 'https://api.anthropic.com/v1', model: 'claude-sonnet-4-6',              requiresKey: true  },
  openai:    { baseURL: 'https://api.openai.com/v1',    model: 'gpt-4o',                         requiresKey: true  },
  custom:    { baseURL: '',                              model: '',                               requiresKey: false },
}

const providerConf = PROVIDER_DEFAULTS[providerFlag] ?? PROVIDER_DEFAULTS.local

// Resolve endpoint
const baseURL = endpointFlag ?? providerConf.baseURL
if (!baseURL) {
  console.error(`Error: --endpoint is required for provider '${providerFlag}'.`)
  process.exit(2)
}

// Resolve model
const MODEL = modelFlag ?? providerConf.model
if (!MODEL) {
  console.error(`Error: --model is required for provider '${providerFlag}'.`)
  process.exit(2)
}

// Resolve API key
let apiKey = apiKeyFlag
if (!apiKey && providerFlag === 'anthropic') apiKey = process.env.ANTHROPIC_API_KEY
if (!apiKey && providerFlag === 'openai')    apiKey = process.env.OPENAI_API_KEY
if (!apiKey && providerConf.requiresKey) {
  console.error(`Error: provider '${providerFlag}' requires an API key. Pass --api-key or set the appropriate env var.`)
  process.exit(2)
}
if (!apiKey) apiKey = 'lm-studio'  // placeholder for local providers

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

const client = new OpenAI({ baseURL, apiKey })

// ---------------------------------------------------------------------------
// Prompt assembly (mirrors evaluator.js)
// ---------------------------------------------------------------------------

function buildSystemPrompt(scenario, artifactContent) {
  const { schema_version = 1.0, domain_name, level, title, delivery_mode, presentation, rubric } = scenario

  let criticalBlock = ''
  let secondaryBlock = ''

  if (schema_version >= 2.0 && rubric.findings) {
    criticalBlock = rubric.findings
      .filter(f => f.type === 'critical')
      .map(f => `[${f.id}] (Severity: critical) ${f.description.trim()}`)
      .join('\n\n')
    
    secondaryBlock = rubric.findings
      .filter(f => f.type === 'secondary')
      .map(f => `[${f.id}] (Severity: secondary) ${f.description.trim()}`)
      .join('\n\n')
  } else {
    criticalBlock = (rubric.critical_findings ?? []).map(f =>
      `[${f.id}] (Severity: ${f.severity}) ${f.description.trim()}`
    ).join('\n\n')

    secondaryBlock = (rubric.secondary_findings ?? []).map(f =>
      `[${f.id}] (Severity: ${f.severity}) ${f.description.trim()}`
    ).join('\n\n')
  }

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

// ---------------------------------------------------------------------------
// Evaluator call
// ---------------------------------------------------------------------------

async function callEvaluator(scenario, artifactContent, responseText, retry = true) {
  const systemPrompt = buildSystemPrompt(scenario, artifactContent)

  const response = await client.chat.completions.create({
    model: MODEL,
    max_tokens: 2048,
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: responseText },
    ],
  })

  const raw = response.choices[0]?.message?.content ?? ''
  const jsonMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/) ?? raw.match(/(\{[\s\S]*\})/)
  const jsonStr = jsonMatch ? (jsonMatch[1] ?? jsonMatch[0]) : raw

  try {
    return JSON.parse(jsonStr.trim())
  } catch (err) {
    if (retry) {
      process.stdout.write(`(parse error, retrying...) `)
      return callEvaluator(scenario, artifactContent, responseText, false)
    }
    return { _parse_error: true, _raw: raw }
  }
}

// ---------------------------------------------------------------------------
// Scenario loading
// ---------------------------------------------------------------------------

function loadScenario(scenarioYamlPath) {
  const content = readFileSync(scenarioYamlPath, 'utf-8')
  return parseYaml(content)
}

function loadArtifact(scenario) {
  const artifactFile = scenario.presentation?.artifact_file
  if (!artifactFile) return null
  const artifactPath = join(REPO_ROOT, artifactFile)
  if (!existsSync(artifactPath)) return null
  return readFileSync(artifactPath, 'utf-8')
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const yamlPaths = await glob('**/scenario.yaml', { cwd: SCENARIOS_DIR, absolute: true })

  if (yamlPaths.length === 0) {
    console.error(`No scenario.yaml files found in ${SCENARIOS_DIR}`)
    process.exit(2)
  }

  // Apply filters
  const filteredPaths = yamlPaths.filter(p => {
    const scenario = loadScenario(p)
    if (scenarioFilter && scenario.id !== scenarioFilter) return false
    if (domainFilter && scenario.domain !== domainFilter) return false
    return true
  })

  if (filteredPaths.length === 0) {
    console.error('No scenarios match the specified filter.')
    process.exit(2)
  }

  console.log(`\nCalibration harness — ${new Date().toISOString()}`)
  console.log(`Provider: ${providerFlag}`)
  console.log(`Endpoint: ${baseURL}`)
  console.log(`Model:    ${MODEL}`)
  console.log(`Scenarios: ${filteredPaths.length}\n`)

  const results = []
  let totalRuns = 0
  let passed = 0
  let failed = 0
  let skipped = 0

  for (const yamlPath of filteredPaths.sort()) {
    const scenarioDir = dirname(yamlPath)
    const scenario = loadScenario(yamlPath)
    const artifactContent = loadArtifact(scenario)
    const scenarioResults = { id: scenario.id, domain: scenario.domain, level: scenario.level, mode: scenario.delivery_mode, runs: [] }

    console.log(`Scenario: ${scenario.id} (Domain ${scenario.domain}, Level ${scenario.level}, Mode ${scenario.delivery_mode})`)

    for (const expectedLevel of EXPECTED_LEVELS) {
      const responseFile = join(scenarioDir, `response_level_${expectedLevel}.txt`)
      if (!existsSync(responseFile)) {
        console.log(`  L${expectedLevel}: [SKIP] response_level_${expectedLevel}.txt not found`)
        skipped++
        scenarioResults.runs.push({ expected: expectedLevel, status: 'skip' })
        continue
      }

      const responseText = readFileSync(responseFile, 'utf-8')

      process.stdout.write(`  L${expectedLevel}: calling evaluator... `)
      try {
        const result = await callEvaluator(scenario, artifactContent, responseText)
        totalRuns++

        if (result._parse_error) {
          console.log(`[ERROR] JSON parse failed`)
          console.log(`        Raw: ${result._raw.slice(0, 200)}`)
          failed++
          scenarioResults.runs.push({ expected: expectedLevel, status: 'error', raw: result._raw })
          continue
        }

        const returnedLevel = result.level
        const deviation = Math.abs(returnedLevel - expectedLevel)
        const pass = deviation <= PASS_TOLERANCE

        if (pass) {
          passed++
          console.log(`[PASS] returned L${returnedLevel} (expected L${expectedLevel})`)
        } else {
          failed++
          console.log(`[FAIL] returned L${returnedLevel} (expected L${expectedLevel}, deviation ${deviation.toFixed(1)})`)
          console.log(`        Gap: ${result.gap ?? 'none'}`)
          console.log(`        Caught: ${(result.caught ?? []).join(', ') || '(none)'}`)
          console.log(`        Missed: ${(result.missed ?? []).join(', ') || '(none)'}`)
        }

        scenarioResults.runs.push({
          expected: expectedLevel,
          returned: returnedLevel,
          confidence: result.confidence,
          deviation,
          pass,
          caught: result.caught ?? [],
          missed: result.missed ?? [],
          gap: result.gap,
          narrative: result.narrative,
          status: pass ? 'pass' : 'fail',
        })
      } catch (err) {
        console.log(`[ERROR] API call failed: ${err.message}`)
        failed++
        scenarioResults.runs.push({ expected: expectedLevel, status: 'error', error: err.message })
      }
    }

    results.push(scenarioResults)
    console.log()
  }

  // Summary
  const totalAttempted = passed + failed
  console.log('─'.repeat(60))
  console.log(`Results: ${passed} passed / ${failed} failed / ${skipped} skipped`)
  if (totalAttempted > 0) {
    console.log(`Pass rate: ${((passed / totalAttempted) * 100).toFixed(0)}%`)
  }
  console.log()

  // Flag scenarios needing rubric adjustment
  const needsAdjustment = results.filter(s =>
    s.runs.filter(r => r.status === 'fail').length >= 2
  )
  if (needsAdjustment.length > 0) {
    console.log('Scenarios with systematic calibration issues (≥2 level mismatches):')
    for (const s of needsAdjustment) {
      const failures = s.runs.filter(r => r.status === 'fail')
      console.log(`  ${s.id}`)
      for (const f of failures) {
        console.log(`    L${f.expected} → returned L${f.returned}: ${f.gap ?? 'no gap note'}`)
      }
    }
    console.log()
    console.log('Action: Adjust miss_signal specificity in the rubric for these scenarios.')
    console.log('See orchestration_design.md (Evaluation Quality Control) for the adjustment procedure.\n')
  }

  // Write JSON results
  mkdirSync(RESULTS_DIR, { recursive: true })
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const resultsFile = join(RESULTS_DIR, `calibration_${timestamp}.json`)
  writeFileSync(resultsFile, JSON.stringify({
    timestamp: new Date().toISOString(),
    provider: providerFlag,
    endpoint: baseURL,
    model: MODEL,
    summary: { total_runs: totalAttempted, passed, failed, skipped },
    scenarios: results,
  }, null, 2))
  console.log(`Full results written to: ${resultsFile}`)

  process.exit(failed > 0 ? 1 : 0)
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(2)
})
