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
import { performEvaluation } from '../core/evaluator.js'

const __dirname = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(__dirname, '..')
const SCENARIOS_DIR = join(REPO_ROOT, 'scenarios')
const RESULTS_DIR = join(__dirname, 'results')
const EXPECTED_LEVELS = [1, 2, 3, 4]
const PASS_TOLERANCE = 0.5

// ---------------------------------------------------------------------------
// Model Registry
// ---------------------------------------------------------------------------

const MODELS = {
  // Local (MLX / LM Studio)
  'qwen3': {
    provider: 'local',
    id: 'qwen3-next-80b-a3b-instruct-mlx',
    baseURL: 'http://192.168.1.28:1234/v1',
    compactRubric: true
  },
  'qwen35-c': {
    provider: 'local',
    id: 'qwen3.5-vl-122b-a10b-mlx-crack-x',
    baseURL: 'http://192.168.1.28:1234/v1',
    compactRubric: true
  },
  'qwen35-3bit': {
    provider: 'local',
    id: 'qwen3.5-122b-a10b-mlx-3-vl',
    baseURL: 'http://192.168.1.28:1234/v1',
    compactRubric: true
  },

  // Anthropic
  'sonnet': {
    provider: 'anthropic',
    id: 'claude-sonnet-4-6',
    baseURL: 'https://api.anthropic.com/v1',
    requiresKey: true,
    compactRubric: false
  },
  'opus': {
    provider: 'anthropic',
    id: 'claude-opus-4-6',
    baseURL: 'https://api.anthropic.com/v1',
    requiresKey: true,
    compactRubric: false
  },

  // OpenAI
  'gpt4o': {
    provider: 'openai',
    id: 'gpt-4o',
    baseURL: 'https://api.openai.com/v1',
    requiresKey: true,
    compactRubric: false
  }
}

const PROVIDER_DEFAULTS = {
  local:     { baseURL: 'http://192.168.1.28:1234/v1', model: 'qwen3-next-80b-a3b-instruct-mlx', requiresKey: false, compactRubric: true  },
  anthropic: { baseURL: 'https://api.anthropic.com/v1', model: 'claude-sonnet-4-6',              requiresKey: true,  compactRubric: false },
  openai:    { baseURL: 'https://api.openai.com/v1',    model: 'gpt-4o',                         requiresKey: true,  compactRubric: false },
  custom:    { baseURL: '',                              model: '',                               requiresKey: false, compactRubric: false },
}

// ---------------------------------------------------------------------------
// CLI args
// ---------------------------------------------------------------------------

const args = process.argv.slice(2)

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
Calibration harness for the sysadmin competency assessment evaluator.

Usage:
  node run.mjs [options]

Options:
  --model <name|alias>   Model name or alias (e.g., qwen3, qwen35, sonnet, gpt4o)
  --provider <name>      Provider (local, anthropic, openai, custom). Default: local
  --endpoint <url>       Override API endpoint
  --api-key <key>        Override API key
  --scenario <id>        Filter by scenario ID (can be used multiple times)
  --domain <n>           Filter by domain number
  --level <n>            Filter by expected level (1-4)
  --list-models          List available model aliases
  --help, -h             Show this help

Aliases:
${Object.keys(MODELS).map(k => `  ${k.padEnd(12)} -> ${MODELS[k].id}`).join('\n')}
`)
  process.exit(0)
}

if (args.includes('--list-models')) {
  console.log('\nAvailable model aliases:')
  for (const [alias, config] of Object.entries(MODELS)) {
    console.log(`  ${alias.padEnd(12)} : ${config.id} (${config.provider})`)
  }
  console.log()
  process.exit(0)
}

function getArg(flag, defaultValue = null) {
  const i = args.indexOf(flag)
  return i !== -1 ? args[i + 1] : defaultValue
}

function getArgs(flag) {
  const values = []
  for (let i = 0; i < args.length; i++) {
    if (args[i] === flag && i + 1 < args.length) values.push(args[i + 1])
  }
  return values
}

const scenarioFilters = getArgs('--scenario')
const domainFilter   = getArg('--domain') ? parseInt(getArg('--domain')) : null
const levelFilter    = getArg('--level') ? parseInt(getArg('--level')) : null
const providerFlag   = getArg('--provider')
const endpointFlag   = getArg('--endpoint')
const modelFlag      = getArg('--model')
const apiKeyFlag     = getArg('--api-key')

// ---------------------------------------------------------------------------
// Configuration Resolution
// ---------------------------------------------------------------------------

let MODEL = modelFlag
let provider = providerFlag
let baseURL = endpointFlag
let apiKey = apiKeyFlag
let compactRubric = false
let requiresKey = false

// 1. Resolve via model alias if it exists
if (MODEL && MODELS[MODEL]) {
  const m = MODELS[MODEL]
  MODEL = m.id
  provider = provider ?? m.provider
  baseURL = baseURL ?? m.baseURL
  compactRubric = m.compactRubric
  requiresKey = m.requiresKey
}

// 2. Resolve provider defaults
provider = provider ?? 'local'
const pConf = PROVIDER_DEFAULTS[provider] ?? PROVIDER_DEFAULTS.local

MODEL = MODEL ?? pConf.model
baseURL = baseURL ?? pConf.baseURL
compactRubric = (modelFlag && MODELS[modelFlag]) ? MODELS[modelFlag].compactRubric : pConf.compactRubric
requiresKey = requiresKey || pConf.requiresKey

if (!MODEL) {
  console.error(`Error: --model is required or could not be resolved for provider '${provider}'.`)
  process.exit(2)
}

if (!baseURL) {
  console.error(`Error: --endpoint is required or could not be resolved for provider '${provider}'.`)
  process.exit(2)
}

// 3. Resolve API key
if (!apiKey && provider === 'anthropic') apiKey = process.env.ANTHROPIC_API_KEY
if (!apiKey && provider === 'openai')    apiKey = process.env.OPENAI_API_KEY
if (!apiKey && requiresKey) {
  console.error(`Error: provider '${provider}' requires an API key. Pass --api-key or set the appropriate env var.`)
  process.exit(2)
}
if (!apiKey) apiKey = 'lm-studio'  // placeholder for local providers

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

const client = new OpenAI({ baseURL, apiKey })

// ---------------------------------------------------------------------------
// Evaluator call
// ---------------------------------------------------------------------------

async function callEvaluator(scenario, artifactContent, responseText, compactRubric = false) {
  return performEvaluation({
    client,
    model: MODEL,
    scenario,
    artifactContent,
    responseText,
    compactRubric
  })
}

// ---------------------------------------------------------------------------
// Scenario loading
// ---------------------------------------------------------------------------

function loadScenario(scenarioYamlPath) {
  const content = readFileSync(scenarioYamlPath, 'utf-8')
  return parseYaml(content)
}

function loadArtifact(scenario) {
  const { schema_version = 1.0, delivery_mode, delivery_modes, presentation } = scenario
  const mode = delivery_mode || (delivery_modes && delivery_modes[0]) || 'A'
  
  const activePresentation = (schema_version >= 2.0 && presentation.modes) 
    ? (presentation.modes[mode] || presentation.modes['A'] || {}) 
    : presentation

  const artifactFile = activePresentation.artifact_file
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
    if (scenarioFilters.length > 0 && !scenarioFilters.includes(scenario.id)) return false
    if (domainFilter && scenario.domain !== domainFilter) return false
    return true
  })

  if (filteredPaths.length === 0) {
    console.error('No scenarios match the specified filter.')
    process.exit(2)
  }

  console.log(`\nCalibration harness — ${new Date().toISOString()}`)
  console.log(`Provider: ${provider}`)
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
    
    // Resolve mode correctly for V1/V2
    const mode = scenario.delivery_mode || (scenario.delivery_modes && scenario.delivery_modes[0]) || 'A'
    
    const artifactContent = loadArtifact(scenario)
    const scenarioResults = { id: scenario.id, domain: scenario.domain, level: scenario.level, mode, runs: [] }

    console.log(`Scenario: ${scenario.id} (Domain ${scenario.domain}, Level ${scenario.level}, Mode ${mode})`)

    for (const expectedLevel of EXPECTED_LEVELS) {
      if (levelFilter && expectedLevel !== levelFilter) continue

      const responseFile = join(scenarioDir, `response_level_${expectedLevel}.txt`)
      if (!existsSync(responseFile)) {
        if (!levelFilter) { // Don't log skips if we're filtering for a specific level
          console.log(`  L${expectedLevel}: [SKIP] response_level_${expectedLevel}.txt not found`)
        }
        skipped++
        scenarioResults.runs.push({ expected: expectedLevel, status: 'skip' })
        continue
      }

      const responseText = readFileSync(responseFile, 'utf-8')

      process.stdout.write(`  L${expectedLevel}: calling evaluator... `)
      try {
        const result = await callEvaluator(scenario, artifactContent, responseText, compactRubric)
        totalRuns++

        if (!result.parsed) {
          console.log(`[ERROR] JSON parse failed`)
          console.log(`        Raw: ${result.raw.slice(0, 200)}`)
          failed++
          scenarioResults.runs.push({ expected: expectedLevel, status: 'error', raw: result.raw })
          continue
        }

        const returnedLevel = result.parsed.level
        const deviation = Math.abs(returnedLevel - expectedLevel)
        const pass = deviation <= PASS_TOLERANCE

        if (pass) {
          passed++
          console.log(`[PASS] returned L${returnedLevel} (expected L${expectedLevel})`)
        } else {
          failed++
          console.log(`[FAIL] returned L${returnedLevel} (expected L${expectedLevel}, deviation ${deviation.toFixed(1)})`)
          console.log(`        Gap: ${result.parsed.gap ?? 'none'}`)
          console.log(`        Caught: ${(result.parsed.caught ?? []).join(', ') || '(none)'}`)
          if (result.parsed.almost_caught && result.parsed.almost_caught.length > 0) {
            console.log(`        Almost: ${result.parsed.almost_caught.join(', ')}`)
          }
          console.log(`        Missed: ${(result.parsed.missed ?? []).join(', ') || '(none)'}`)
          if (result.parsed.narrative) {
            console.log(`        Narrative: ${result.parsed.narrative.split('\n')[0]}...`)
          }
        }

        scenarioResults.runs.push({
          expected: expectedLevel,
          returned: returnedLevel,
          confidence: result.parsed.confidence,
          deviation,
          pass,
          caught: result.parsed.caught ?? [],
          missed: result.parsed.missed ?? [],
          gap: result.parsed.gap,
          narrative: result.parsed.narrative,
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
