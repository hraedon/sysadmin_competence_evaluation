/**
 * Capability profile — persisted to localStorage.
 *
 * Schema:
 * {
 *   updated: ISO string,
 *   domains: {
 *     [domain_number]: {
 *       domain_name: string,
 *       results: [{ scenario_id, title, level, confidence, gap, timestamp }]
 *     }
 *   }
 * }
 *
 * Note: gap was added in Phase B++. Existing results without it degrade cleanly (gap is null).
 */

const KEY = 'sysadmin_assessment_profile'
const ONBOARDING_KEY = 'sysadmin_onboarding_dismissed'
const REVIEW_THRESHOLD_DAYS = 14

export function loadProfile() {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? JSON.parse(raw) : { updated: null, domains: {} }
  } catch {
    return { updated: null, domains: {} }
  }
}

export function saveResult({ scenario, level, confidence, gap, almost_caught }) {
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
    gap: gap ?? null,
    almost_caught: almost_caught ?? [],
    timestamp: new Date().toISOString(),
  })
  profile.updated = new Date().toISOString()
  localStorage.setItem(KEY, JSON.stringify(profile))
  return profile
}

/**
 * Returns the assessed level for a domain using the median of all results.
 * More stable than most-recent: one outlier run doesn't drag the level down.
 * Returns null if no results exist.
 */
export function domainLevel(profile, domain) {
  const d = profile.domains[domain]
  if (!d || !d.results.length) return null
  const levels = [...d.results].map(r => r.level).sort((a, b) => a - b)
  const mid = Math.floor(levels.length / 2)
  return levels.length % 2 === 0
    ? Math.floor((levels[mid - 1] + levels[mid]) / 2)
    : levels[mid]
}

/**
 * Returns the recommended next scenario for a domain.
 * Prefers the lowest-difficulty scenario at assessed_level + 1,
 * falling back to same level, then any uncompleted scenario.
 * Returns null if all scenarios in the domain are completed.
 */
export function recommendNext(allScenarios, profile, domain) {
  const results = profile.domains[domain]?.results ?? []
  const completedIds = new Set(results.map(r => r.scenario_id))
  const assessed = domainLevel(profile, domain)

  const available = allScenarios
    .filter(s => s.domain === Number(domain) && !completedIds.has(s.id))
    .sort((a, b) => (a.level - b.level) || ((a.difficulty ?? 3) - (b.difficulty ?? 3)))

  if (!assessed) return available[0] ?? null

  const targetLevel = assessed + 1
  return (
    available.find(s => s.level === targetLevel) ??
    available.find(s => s.level === assessed) ??
    available[0] ?? null
  )
}

/**
 * Returns scenarios whose most-recent attempt is older than REVIEW_THRESHOLD_DAYS.
 * One entry per scenario_id (most recent attempt), sorted most-stale first.
 */
export function staleScenariosForReview(profile) {
  const threshold = Date.now() - REVIEW_THRESHOLD_DAYS * 24 * 60 * 60 * 1000
  const byScenario = new Map()

  for (const [domain, data] of Object.entries(profile.domains ?? {})) {
    for (const r of data.results) {
      const existing = byScenario.get(r.scenario_id)
      if (!existing || r.timestamp > existing.timestamp) {
        byScenario.set(r.scenario_id, { ...r, domain: Number(domain), domain_name: data.domain_name })
      }
    }
  }

  return Array.from(byScenario.values())
    .filter(r => new Date(r.timestamp).getTime() < threshold)
    .sort((a, b) => a.timestamp.localeCompare(b.timestamp))
}

export function clearProfile() {
  localStorage.removeItem(KEY)
}

export function isOnboardingDismissed() {
  return !!localStorage.getItem(ONBOARDING_KEY)
}

export function dismissOnboarding() {
  localStorage.setItem(ONBOARDING_KEY, '1')
}
