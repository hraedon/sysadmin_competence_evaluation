import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'

function generate(mode) {
  execFileSync(process.execPath, ['scripts/generate-manifest.mjs'], {
    env: { ...process.env, VITE_EVALUATION_MODE: mode },
    stdio: 'pipe',
  })
  return JSON.parse(readFileSync('public/scenarios-manifest.json', 'utf8'))
}

const local = generate('local')
const server = generate('server')
assert.ok(local.length > 0, 'local manifest must contain scenarios')
assert.ok(local.some(scenario => scenario.rubric), 'local mode must retain rubrics')
assert.ok(server.every(scenario => !scenario.rubric), 'server mode must strip every rubric')
generate('local')
console.log('evaluation mode manifest checks passed')
