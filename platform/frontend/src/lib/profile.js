/**
 * Capability profile — persisted to localStorage.
 *
 * Schema:
 * {
 *   updated: ISO string,
 *   domains: {
 *     [domain_number]: {
 *       domain_name: string,
 *       results: [{ scenario_id, level, confidence, timestamp }]
 *     }
 *   }
 * }
 */

const KEY = 'sysadmin_assessment_profile'

export function loadProfile() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : { updated: null, domains: {} }
  } catch {
    return { updated: null, domains: {} }
  }
}

export function saveResult({ scenario, level, confidence }) {
  const profile = loadProfile()
  const d = scenario.domain
  if (!profile.domains[d]) {
    profile.domains[d] = { domain_name: scenario.domain_name, results: [] }
  }
  // Replace any prior result for this scenario
  profile.domains[d].results = profile.domains[d].results.filter(r => r.scenario_id !== scenario.id)
  profile.domains[d].results.push({
    scenario_id: scenario.id,
    title: scenario.title,
    level,
    confidence,
    timestamp: new Date().toISOString(),
  })
  profile.updated = new Date().toISOString()
  localStorage.setItem(KEY, JSON.stringify(profile))
  return profile
}

/** Returns the highest-confidence level estimate for a domain, or null. */
export function domainLevel(profile, domain) {
  const d = profile.domains[domain]
  if (!d || !d.results.length) return null
  // Use the most recent result
  const sorted = [...d.results].sort((a, b) => b.timestamp.localeCompare(a.timestamp))
  return sorted[0].level
}

export function clearProfile() {
  localStorage.removeItem(KEY)
}
