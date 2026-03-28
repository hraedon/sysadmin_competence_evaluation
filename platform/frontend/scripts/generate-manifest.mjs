/**
 * Prebuild script: walks the scenarios directory and writes a JSON manifest
 * containing the full parsed YAML for every scenario.yaml found.
 *
 * Usage: node scripts/generate-manifest.mjs
 *
 * Environment:
 *   SCENARIOS_DIR  Path to the scenarios root, relative to this script's CWD.
 *                  Defaults to '../../scenarios' (local dev from platform/frontend/).
 *                  Set to '../scenarios' in the Docker build (WORKDIR /build/frontend,
 *                  scenarios at /build/scenarios).
 *
 * Output: public/scenarios-manifest.json
 */

import { readFileSync, writeFileSync, readdirSync, statSync, mkdirSync } from 'fs'
import { join, resolve, relative } from 'path'
import { load as parseYaml } from 'js-yaml'

const SCENARIOS_DIR = resolve(process.cwd(), process.env.SCENARIOS_DIR ?? '../../scenarios')
const OUTPUT_FILE   = resolve(process.cwd(), 'public/scenarios-manifest.json')

function walk(dir) {
  const results = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) {
      results.push(...walk(full))
    } else if (entry === 'scenario.yaml') {
      results.push(full)
    }
  }
  return results
}

const yamlFiles = walk(SCENARIOS_DIR)
const scenarios = []

for (const file of yamlFiles) {
  try {
    const raw = readFileSync(file, 'utf8')
    const data = parseYaml(raw)
    
    if (!data) {
      console.warn(`Skipping empty file: ${file}`)
      continue
    }
    
    // Normalize Schema V2 to V1 for the current frontend
    if (data.schema_version >= 2.0) {
      // 1. Map first delivery mode to the legacy delivery_mode field
      let mode = data.delivery_mode
      if (Array.isArray(data.delivery_modes) && data.delivery_modes.length > 0) {
        mode = data.delivery_modes[0]
        data.delivery_mode = mode
      }
      
      // 2. Extract presentation for the active mode (fallback to A)
      const activeMode = mode || 'A'
      const activePresentation = data.presentation?.modes?.[activeMode] || data.presentation?.modes?.A
      
      if (activePresentation) {
        // Preserve the full modes block for the frontend (needed for Mode E)
        const modes = data.presentation.modes
        data.presentation = {
          type: activePresentation.type,
          artifact_file: activePresentation.artifact_file,
          context: activePresentation.context,
          modes: modes // Re-attach modes so LabPanel can find its data
        }
      }

      // 3. Normalize rubric findings for backward compatibility with EvalPanel.jsx
      if (data.rubric && Array.isArray(data.rubric.findings)) {
        data.rubric.critical_findings = data.rubric.findings.filter(f => f.type === 'critical')
        data.rubric.secondary_findings = data.rubric.findings.filter(f => f.type === 'secondary')
      }

      // 4. Normalize difficulty to a number
      if (typeof data.difficulty === 'object' && data.difficulty !== null) {
        data.difficulty = data.difficulty.score
      }
      if (data.difficulty) {
        data.difficulty = Number(data.difficulty)
      }
    }

    // Strip rubric data from the public manifest.
    //
    // VITE_EVALUATION_MODE controls how much is stripped:
    //   "server" (default): Strip the entire rubric block. Evaluation is server-side
    //       (POST /api/evaluate) so the browser never needs rubric data. This closes
    //       SEC-05 fully — no finding descriptions, miss_signal, or level_indicators
    //       reach the browser. Learning notes are returned by the server after eval.
    //   "local": Strip only answer-key fields (miss_signal, level_indicators) but keep
    //       finding descriptions. Needed for air-gapped/LM Studio deployments where
    //       evaluation runs client-side via core/evaluator.js.
    const evalMode = process.env.VITE_EVALUATION_MODE ?? 'server'

    if (evalMode === 'server') {
      // Full strip: remove entire rubric — server handles everything
      delete data.rubric
    } else if (data.rubric) {
      // Local mode: strip only answer-key fields, keep descriptions for client-side eval
      delete data.rubric.level_indicators
      for (const finding of data.rubric.findings ?? []) {
        delete finding.miss_signal
      }
      for (const finding of data.rubric.critical_findings ?? []) {
        delete finding.miss_signal
      }
      for (const finding of data.rubric.secondary_findings ?? []) {
        delete finding.miss_signal
      }
    }

    // Store the path relative to SCENARIOS_DIR so the frontend can build fetch URLs
    data._scenarios_path = 'scenarios/' + relative(SCENARIOS_DIR, file).replace(/\\/g, '/').replace('scenario.yaml', '').replace(/\/$/, '')
    scenarios.push(data)
  } catch (err) {
    console.warn(`Skipping ${file}: ${err.message}`)
  }
}

scenarios.sort((a, b) => {
  if (a.domain !== b.domain) return a.domain - b.domain
  return (a.level ?? 0) - (b.level ?? 0)
})

mkdirSync(resolve(process.cwd(), 'public'), { recursive: true })
writeFileSync(OUTPUT_FILE, JSON.stringify(scenarios, null, 2))
console.log(`Wrote ${scenarios.length} scenarios to ${OUTPUT_FILE}`)
