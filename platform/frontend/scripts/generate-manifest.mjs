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
    
    // Normalize Schema V2 to V1 for the current frontend
    if (data.schema_version >= 2.0) {
      // 1. Map first delivery mode to the legacy delivery_mode field
      if (Array.isArray(data.delivery_modes) && data.delivery_modes.length > 0) {
        data.delivery_mode = data.delivery_modes[0]
      }
      
      // 2. Extract Mode A presentation for the current static UI
      const modeA = data.presentation?.modes?.A
      if (modeA) {
        data.presentation = {
          type: modeA.type,
          artifact_file: modeA.artifact_file,
          context: modeA.context
        }
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
