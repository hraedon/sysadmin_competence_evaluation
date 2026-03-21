/**
 * Scenario loading and caching.
 *
 * The manifest (public/scenarios-manifest.json) is generated at build time by
 * scripts/generate-manifest.mjs. It contains the full parsed YAML for every
 * scenario, sorted by domain then level.
 *
 * Artifact file content is fetched on demand and cached in memory.
 */

let _manifest = null
const _artifactCache = new Map()

export async function loadManifest() {
  if (_manifest) return _manifest
  const res = await fetch('/scenarios-manifest.json')
  if (!res.ok) throw new Error(`Failed to load scenarios manifest: ${res.status}`)
  _manifest = await res.json()
  return _manifest
}

export async function loadArtifact(artifactFile) {
  if (!artifactFile) return null
  if (_artifactCache.has(artifactFile)) return _artifactCache.get(artifactFile)
  // artifact_file paths start with "scenarios/..." — serve directly as static assets
  const res = await fetch(`/${artifactFile}`)
  if (!res.ok) return null
  const text = await res.text()
  _artifactCache.set(artifactFile, text)
  return text
}

/** Group a flat scenario list by domain number. */
export function groupByDomain(scenarios) {
  const map = new Map()
  for (const s of scenarios) {
    if (!map.has(s.domain)) map.set(s.domain, { domain: s.domain, domain_name: s.domain_name, scenarios: [] })
    map.get(s.domain).scenarios.push(s)
  }
  return Array.from(map.values()).sort((a, b) => a.domain - b.domain)
}
