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
  --concurrency <n>      Max parallel evaluator calls (default: 5, min: 1)
  --mixed                Enable mixed-signal response testing (response_level_mixed.txt)
  --variance <n>         Run each response N times and check level consistency (default: 1)
  --validate-only        Validate scenario structure without calling any API (no key needed)
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
const concurrencyArg = getArg('--concurrency')

if (args.includes('--concurrency') && !concurrencyArg) {
  console.error('Error: --concurrency requires a value (e.g., --concurrency 5).')
  process.exit(2)
}

let concurrency = concurrencyArg ? parseInt(concurrencyArg, 10) : 5
if (!Number.isInteger(concurrency) || concurrency < 1) {
  console.error(`Error: --concurrency must be a positive integer (got '${concurrencyArg}').`)
  process.exit(2)
}

const mixedFlag = args.includes('--mixed')
const validateOnly = args.includes('--validate-only')

const varianceArg = getArg('--variance')
let variance = 1
if (args.includes('--variance')) {
  if (!varianceArg) {
    console.error('Error: --variance requires a value (e.g., --variance 3).')
    process.exit(2)
  }
  variance = parseInt(varianceArg, 10)
  if (!Number.isInteger(variance) || variance < 1) {
    console.error(`Error: --variance must be a positive integer (got '${varianceArg}').`)
    process.exit(2)
  }
}

// ---------------------------------------------------------------------------
// Validate-only mode: structural validation without API calls
// ---------------------------------------------------------------------------

if (validateOnly) {
  const yamlPaths = await glob('**/scenario.yaml', { cwd: SCENARIOS_DIR, absolute: true })

  if (yamlPaths.length === 0) {
    console.error(`No scenario.yaml files found in ${SCENARIOS_DIR}`)
    process.exit(2)
  }

  const filteredPaths = yamlPaths.filter(p => {
    const scenario = loadScenario(p)
    if (scenarioFilters.length > 0 && !scenarioFilters.includes(scenario.id)) return false
    if (domainFilter && scenario.domain !== domainFilter) return false
    return true
  })

  const sortedPaths = filteredPaths.sort()
  let errors = 0
  let warnings = 0
  let checked = 0

  console.log(`\nValidate-only — ${new Date().toISOString()}`)
  console.log(`Scenarios: ${sortedPaths.length}\n`)

  for (const yamlPath of sortedPaths) {
    const scenarioDir = dirname(yamlPath)
    const scenarioId = yamlPath.split('/').slice(-2)[0]
    const issues = []

    let scenario
    try {
      scenario = loadScenario(yamlPath)
    } catch (e) {
      console.log(`  [FAIL] ${scenarioId}: YAML parse error: ${e.message}`)
      errors++
      checked++
      continue
    }

    if (!scenario.id) issues.push('missing id')
    if (!scenario.domain) issues.push('missing domain')
    if (!scenario.domain_name) issues.push('missing domain_name')
    if (!scenario.level) issues.push('missing level')
    if (!scenario.delivery_modes && !scenario.delivery_mode) issues.push('missing delivery_modes/delivery_mode')
    if (!scenario.presentation) issues.push('missing presentation')
    if (!scenario.rubric) issues.push('missing rubric')
    if (scenario.rubric) {
      if (!scenario.rubric.findings || scenario.rubric.findings.length === 0) issues.push('rubric has no findings')
      if (!scenario.rubric.level_indicators) issues.push('rubric missing level_indicators')
      else {
        for (const lvl of ['level_1', 'level_2', 'level_3', 'level_4']) {
          if (!scenario.rubric.level_indicators[lvl]) issues.push(`rubric missing ${lvl}`)
        }
      }
      for (const f of scenario.rubric.findings ?? []) {
        if (!f.id) issues.push(`finding missing id`)
        if (!f.description) issues.push(`finding '${f.id}' missing description`)
        if (!f.severity && !f.type) issues.push(`finding '${f.id}' missing severity/type`)
      }
    }

    const mode = scenario.delivery_mode || (scenario.delivery_modes && scenario.delivery_modes[0]) || 'A'
    const activePresentation = (scenario.schema_version >= 2.0 && scenario.presentation?.modes)
      ? (scenario.presentation.modes[mode] || scenario.presentation.modes['A'] || {})
      : scenario.presentation
    const artifactFile = activePresentation?.artifact_file
    if (artifactFile) {
      const artifactPath = join(REPO_ROOT, artifactFile)
      if (!existsSync(artifactPath)) issues.push(`artifact file not found: ${artifactFile}`)
    }

    for (const expectedLevel of EXPECTED_LEVELS) {
      const responseFile = join(scenarioDir, `response_level_${expectedLevel}.txt`)
      if (!existsSync(responseFile)) issues.push(`missing response_level_${expectedLevel}.txt`)
    }

    if (scenario.rubric?.mixed_signal) {
      if (typeof scenario.rubric.mixed_signal.expected_level !== 'number') {
        issues.push('mixed_signal.expected_level missing or not a number')
      }
      const mixedFile = join(scenarioDir, 'response_level_mixed.txt')
      if (!existsSync(mixedFile)) issues.push('missing response_level_mixed.txt (mixed_signal configured)')
    }

    if (issues.length === 0) {
      console.log(`  [OK]   ${scenario.id}`)
    } else {
      console.log(`  [WARN] ${scenario.id}: ${issues.join('; ')}`)
      warnings++
    }
    checked++
  }

  console.log('\n' + '─'.repeat(60))
  console.log(`Validated: ${checked} scenarios / ${checked - warnings} OK / ${warnings} with issues`)
  if (warnings === 0) {
    console.log('All scenarios pass structural validation.')
  }
  process.exit(warnings > 0 ? 1 : 0)
}

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
// Concurrency pool
// ---------------------------------------------------------------------------

async function runWithConcurrency(tasks, limit, fn) {
  const results = new Array(tasks.length)
  let index = 0
  async function worker() {
    while (index < tasks.length) {
      const i = index++
      results[i] = await fn(tasks[i], i)
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, tasks.length) }, () => worker()))
  return results
}

async function runTask(task) {
  const { scenario, expectedLevel, responseFile, artifactContent, taskType = 'standard', variance: varianceN = 1 } = task
  const isMixed = taskType === 'mixed'
  const levelLabel = isMixed ? 'mixed' : `L${expectedLevel}`
  const prefix = `[${scenario.id}/${levelLabel}]`

  if (!existsSync(responseFile)) {
    if (isMixed || !levelFilter) {
      console.log(`${prefix} [SKIP] response file not found`)
    }
    return { expected: expectedLevel, status: 'skip', taskType }
  }

  const responseText = readFileSync(responseFile, 'utf-8')
  const numRuns = Math.max(1, varianceN)

  try {
    const runResults = []
    for (let v = 0; v < numRuns; v++) {
      const result = await callEvaluator(scenario, artifactContent, responseText, compactRubric)
      runResults.push(result)
    }

    const primary = runResults[0]

    if (!primary.parsed) {
      console.log(`${prefix} [ERROR] JSON parse failed`)
      console.log(`${prefix}        Raw: ${primary.raw.slice(0, 200)}`)
      return { expected: expectedLevel, status: 'error', raw: primary.raw, taskType }
    }

    const returnedLevel = primary.parsed.level
    const deviation = Math.abs(returnedLevel - expectedLevel)

    let pass = null
    let inRange = null
    let status

    if (isMixed) {
      if (expectedLevel === null) {
        status = 'mixed_info'
        console.log(`${prefix} [MIXED] returned L${returnedLevel} (no expected level configured)`)
      } else {
        inRange = deviation <= PASS_TOLERANCE
        pass = inRange
        status = inRange ? 'mixed_in' : 'mixed_out'
        if (inRange) {
          console.log(`${prefix} [MIXED] returned L${returnedLevel} (in range of ${expectedLevel})`)
        } else {
          console.log(`${prefix} [MIXED-OUT] returned L${returnedLevel} (expected ~${expectedLevel}, deviation ${deviation.toFixed(1)})`)
          console.log(`${prefix}        Gap: ${primary.parsed.gap ?? 'none'}`)
          console.log(`${prefix}        Caught: ${(primary.parsed.caught ?? []).join(', ') || '(none)'}`)
          console.log(`${prefix}        Missed: ${(primary.parsed.missed ?? []).join(', ') || '(none)'}`)
        }
      }
    } else {
      pass = deviation <= PASS_TOLERANCE
      status = pass ? 'pass' : 'fail'
      if (pass) {
        console.log(`${prefix} [PASS] returned L${returnedLevel} (expected L${expectedLevel})`)
      } else {
        console.log(`${prefix} [FAIL] returned L${returnedLevel} (expected L${expectedLevel}, deviation ${deviation.toFixed(1)})`)
        console.log(`${prefix}        Gap: ${primary.parsed.gap ?? 'none'}`)
        console.log(`${prefix}        Caught: ${(primary.parsed.caught ?? []).join(', ') || '(none)'}`)
        if (primary.parsed.almost_caught && primary.parsed.almost_caught.length > 0) {
          console.log(`${prefix}        Almost: ${primary.parsed.almost_caught.join(', ')}`)
        }
        console.log(`${prefix}        Missed: ${(primary.parsed.missed ?? []).join(', ') || '(none)'}`)
        if (primary.parsed.narrative) {
          console.log(`${prefix}        Narrative: ${primary.parsed.narrative.split('\n')[0]}...`)
        }
      }
    }

    let varianceData = null
    if (numRuns > 1) {
      const allLevels = runResults
        .map(r => r.parsed?.level)
        .filter(l => typeof l === 'number')
      if (allLevels.length > 0) {
        const minLevel = Math.min(...allLevels)
        const maxLevel = Math.max(...allLevels)
        const maxDev = maxLevel - minLevel
        const showedVariance = maxDev > PASS_TOLERANCE
        varianceData = {
          levels: allLevels,
          min: minLevel,
          max: maxLevel,
          maxDeviation: maxDev,
          showedVariance,
        }
        if (showedVariance) {
          console.log(`${prefix} [VAR] levels across ${numRuns} runs: ${allLevels.join(', ')} (max deviation ${maxDev.toFixed(1)})`)
        }
      }
    }

    return {
      expected: expectedLevel,
      returned: returnedLevel,
      confidence: primary.parsed.confidence,
      deviation,
      pass,
      caught: primary.parsed.caught ?? [],
      missed: primary.parsed.missed ?? [],
      gap: primary.parsed.gap,
      narrative: primary.parsed.narrative,
      status,
      taskType,
      variance: varianceData,
    }
  } catch (err) {
    console.log(`${prefix} [ERROR] API call failed: ${err.message}`)
    return { expected: expectedLevel, status: 'error', error: err.message, taskType }
  }
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

  const sortedPaths = filteredPaths.sort()

  console.log(`\nCalibration harness — ${new Date().toISOString()}`)
  console.log(`Provider: ${provider}`)
  console.log(`Endpoint: ${baseURL}`)
  console.log(`Model:    ${MODEL}`)
  console.log(`Scenarios: ${sortedPaths.length}`)
  console.log(`Concurrency: ${concurrency}`)
  if (mixedFlag)   console.log(`Mixed-signal: enabled`)
  if (variance > 1) console.log(`Variance: ${variance} runs per response`)
  console.log()

  const results = []
  const tasks = []
  for (const yamlPath of sortedPaths) {
    const scenarioDir = dirname(yamlPath)
    const scenario = loadScenario(yamlPath)
    const mode = scenario.delivery_mode || (scenario.delivery_modes && scenario.delivery_modes[0]) || 'A'
    const artifactContent = loadArtifact(scenario)
    const scenarioResults = { id: scenario.id, domain: scenario.domain, level: scenario.level, mode, runs: [] }
    results.push(scenarioResults)
    for (const expectedLevel of EXPECTED_LEVELS) {
      if (levelFilter && expectedLevel !== levelFilter) continue
      const responseFile = join(scenarioDir, `response_level_${expectedLevel}.txt`)
      tasks.push({ scenario, expectedLevel, responseFile, artifactContent, scenarioResults, taskType: 'standard', variance })
    }
    if (mixedFlag) {
      const mixedFile = join(scenarioDir, 'response_level_mixed.txt')
      const mixedConfig = scenario.rubric?.mixed_signal
      const mixedExpected = mixedConfig?.expected_level ?? null
      tasks.push({
        scenario,
        expectedLevel: mixedExpected,
        responseFile: mixedFile,
        artifactContent,
        scenarioResults,
        taskType: 'mixed',
        variance,
      })
    }
  }

  const taskResults = await runWithConcurrency(tasks, concurrency, runTask)

  for (let i = 0; i < tasks.length; i++) {
    tasks[i].scenarioResults.runs.push(taskResults[i])
  }

  const standardResults = taskResults.filter(r => r.taskType !== 'mixed')
  const mixedResults = taskResults.filter(r => r.taskType === 'mixed')

  const passed = standardResults.filter(r => r.status === 'pass').length
  const failed = standardResults.filter(r => r.status === 'fail' || r.status === 'error').length
  const skipped = standardResults.filter(r => r.status === 'skip').length

  const mixedTested = mixedResults.filter(r => r.status === 'mixed_in' || r.status === 'mixed_out' || r.status === 'mixed_info').length
  const mixedInRange = mixedResults.filter(r => r.status === 'mixed_in').length
  const mixedOutOfRange = mixedResults.filter(r => r.status === 'mixed_out').length
  const mixedInfo = mixedResults.filter(r => r.status === 'mixed_info').length
  const mixedErrors = mixedResults.filter(r => r.status === 'error').length

  const varianceScenarios = results.filter(s => s.runs.some(r => r.variance))
  const varianceTested = varianceScenarios.reduce((sum, s) => sum + s.runs.filter(r => r.variance).length, 0)
  const varianceShowed = results.reduce((sum, s) => sum + s.runs.filter(r => r.variance?.showedVariance).length, 0)
  const varianceMaxDeviation = taskResults.length > 0
    ? Math.max(0, ...taskResults.map(r => r.variance?.maxDeviation ?? 0))
    : 0

  for (const s of results) {
    const vRuns = s.runs.filter(r => r.variance)
    if (vRuns.length > 0) {
      s.variance = {
        tested: vRuns.length,
        showedVariance: vRuns.filter(r => r.variance.showedVariance).length,
        maxDeviation: Math.max(...vRuns.map(r => r.variance.maxDeviation)),
        details: vRuns.map(r => ({
          level: r.expected,
          levels: r.variance.levels,
          maxDeviation: r.variance.maxDeviation,
          showedVariance: r.variance.showedVariance,
        })),
      }
    }
  }

  // Summary
  const totalAttempted = passed + failed
  console.log('─'.repeat(60))
  console.log(`Results: ${passed} passed / ${failed} failed / ${skipped} skipped`)
  if (totalAttempted > 0) {
    console.log(`Pass rate: ${((passed / totalAttempted) * 100).toFixed(0)}%`)
  }
  if (mixedFlag) {
    const infoPart = mixedInfo > 0 ? ` / ${mixedInfo} info-only` : ''
    console.log(`Mixed: ${mixedTested} tested / ${mixedInRange} in range / ${mixedOutOfRange} out of range${infoPart}`)
  }
  if (variance > 1) {
    console.log(`Variance: ${varianceTested} responses tested / ${varianceShowed} showed variance / max deviation: ${varianceMaxDeviation.toFixed(1)}`)
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

  // Flag scenarios with variance
  const varianceFlags = results.filter(s => s.variance?.showedVariance > 0)
  if (varianceFlags.length > 0) {
    console.log('Scenarios with evaluator variance (level changed across runs):')
    for (const s of varianceFlags) {
      const varied = s.variance.details.filter(d => d.showedVariance)
      console.log(`  ${s.id}`)
      for (const d of varied) {
        const label = d.level === null ? 'mixed' : `L${d.level}`
        console.log(`    ${label}: levels [${d.levels.join(', ')}] (max deviation ${d.maxDeviation.toFixed(1)})`)
      }
    }
    console.log()
  }

  // Write JSON results
  mkdirSync(RESULTS_DIR, { recursive: true })
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19)
  const resultsFile = join(RESULTS_DIR, `calibration_${timestamp}.json`)

  const summary = { total_runs: totalAttempted, passed, failed, skipped }
  if (mixedFlag) {
    summary.mixed = {
      tested: mixedTested,
      inRange: mixedInRange,
      outOfRange: mixedOutOfRange,
      infoOnly: mixedInfo,
    }
  }
  if (variance > 1) {
    summary.variance = {
      responsesTested: varianceTested,
      showedVariance: varianceShowed,
      maxDeviation: varianceMaxDeviation,
    }
  }

  writeFileSync(resultsFile, JSON.stringify({
    timestamp: new Date().toISOString(),
    provider: provider,
    endpoint: baseURL,
    model: MODEL,
    summary,
    scenarios: results,
  }, null, 2))
  console.log(`Full results written to: ${resultsFile}`)

  const hasFailures = failed > 0 || mixedOutOfRange > 0 || mixedErrors > 0
  process.exit(hasFailures ? 1 : 0)
}

main().catch(err => {
  console.error('Fatal error:', err)
  process.exit(2)
})
