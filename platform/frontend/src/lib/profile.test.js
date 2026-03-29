import { describe, it, expect, beforeEach, vi } from 'vitest'

// ── localStorage shim for JSDOM/Vitest ──────────────────────────────────────────
// Vitest with jsdom already has localStorage, but we can clear it
const clearStore = () => localStorage.clear()

const { loadProfile, saveResult, domainLevel, recommendNext, staleScenariosForReview, clearProfile, isOnboardingDismissed, dismissOnboarding } = await import('./profile.js')

// ── Fixtures ─────────────────────────────────────────────────────────────
const mkScenario = (overrides) => ({
  id: 'd01-test-scenario',
  domain: 1,
  domain_name: 'Scripting and Automation',
  title: 'Test Scenario',
  level: 2,
  difficulty: 3,
  ...overrides,
})

describe('loadProfile', () => {
  beforeEach(() => clearStore())

  it('returns empty profile when localStorage is empty', () => {
    const p = loadProfile()
    expect(p.domains).toEqual({})
    expect(p.updated).toBeNull()
  })

  it('returns empty profile when localStorage contains invalid JSON', () => {
    localStorage.setItem('sysadmin_assessment_profile', 'not json')
    const p = loadProfile()
    expect(p.domains).toEqual({})
  })
})

describe('saveResult', () => {
  beforeEach(() => clearStore())

  it('creates domain entry on first save', () => {
    const s = mkScenario()
    const p = saveResult({ scenario: s, level: 2, confidence: 'high', gap: null })
    expect(p.domains[1].domain_name).toBe('Scripting and Automation')
    expect(p.domains[1].results.length).toBe(1)
    expect(p.domains[1].results[0].level).toBe(2)
  })

  it('replaces prior result for same scenario_id', () => {
    const s = mkScenario()
    saveResult({ scenario: s, level: 1, confidence: 'low', gap: 'missed everything' })
    const p = saveResult({ scenario: s, level: 3, confidence: 'high', gap: null })
    expect(p.domains[1].results.length).toBe(1)
    expect(p.domains[1].results[0].level).toBe(3)
  })

  it('preserves results from different scenarios in same domain', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 2, confidence: 'medium', gap: null })
    const p = saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'high', gap: null })
    expect(p.domains[1].results.length).toBe(2)
  })

  it('persists gap field', () => {
    const p = saveResult({ scenario: mkScenario(), level: 2, confidence: 'medium', gap: 'needs error handling' })
    expect(p.domains[1].results[0].gap).toBe('needs error handling')
  })

  it('persists almost_caught field', () => {
    const p = saveResult({
      scenario: mkScenario(),
      level: 2,
      confidence: 'medium',
      gap: null,
      almost_caught: ['finding_a', 'finding_b'],
    })
    expect(p.domains[1].results[0].almost_caught).toEqual(['finding_a', 'finding_b'])
  })

  it('defaults almost_caught to empty array when omitted', () => {
    const p = saveResult({ scenario: mkScenario(), level: 2, confidence: 'high', gap: null })
    expect(p.domains[1].results[0].almost_caught).toEqual([])
  })

  it('round-trips through localStorage', () => {
    saveResult({ scenario: mkScenario(), level: 3, confidence: 'high', gap: 'a gap' })
    const reloaded = loadProfile()
    expect(reloaded.domains[1].results[0].level).toBe(3)
    expect(reloaded.domains[1].results[0].gap).toBe('a gap')
  })
})

describe('domainLevel — median logic', () => {
  beforeEach(() => clearStore())

  it('returns null for empty domain', () => {
    expect(domainLevel(loadProfile(), 1)).toBeNull()
  })

  it('returns the single result level', () => {
    saveResult({ scenario: mkScenario(), level: 3, confidence: 'high', gap: null })
    expect(domainLevel(loadProfile(), 1)).toBe(3)
  })

  it('returns median of odd count', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 1, confidence: 'low', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-c' }), level: 4, confidence: 'high', gap: null })
    expect(domainLevel(loadProfile(), 1)).toBe(3)
  })

  it('returns floor of average for even count', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 2, confidence: 'medium', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'medium', gap: null })
    // (2+3)/2 = 2.5 → floor → 2
    expect(domainLevel(loadProfile(), 1)).toBe(2)
  })

  it('handles single outlier without dragging median', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-c' }), level: 1, confidence: 'low', gap: null })
    expect(domainLevel(loadProfile(), 1)).toBe(3)
  })
})

describe('recommendNext', () => {
  beforeEach(() => clearStore())

  const scenarios = [
    mkScenario({ id: 'd01-a', level: 1, difficulty: 2 }),
    mkScenario({ id: 'd01-b', level: 2, difficulty: 3 }),
    mkScenario({ id: 'd01-c', level: 3, difficulty: 4 }),
    mkScenario({ id: 'd01-d', level: 3, difficulty: 5 }),
  ]

  it('returns lowest-difficulty scenario when no prior results', () => {
    const next = recommendNext(scenarios, loadProfile(), 1)
    expect(next.id).toBe('d01-a')
  })

  it('recommends next level up after assessment', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 1, confidence: 'medium', gap: null })
    const next = recommendNext(scenarios, loadProfile(), 1)
    expect(next.id).toBe('d01-b')
  })

  it('returns null when all scenarios completed', () => {
    for (const s of scenarios) {
      saveResult({ scenario: s, level: s.level, confidence: 'high', gap: null })
    }
    const next = recommendNext(scenarios, loadProfile(), 1)
    expect(next).toBeNull()
  })

  it('falls back to same-level scenario if next level not available', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-c' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 1, confidence: 'low', gap: null })
    // median of [1,3] = floor(2) = 2 → looks for L3, finds d01-d
    const next = recommendNext(scenarios, loadProfile(), 1)
    // assessed = 2, target = 3, d01-c already done → d01-d is L3 and available
    expect(next.id).toBe('d01-d')
  })
})

describe('staleScenariosForReview', () => {
  beforeEach(() => clearStore())

  it('returns empty for fresh results', () => {
    saveResult({ scenario: mkScenario(), level: 2, confidence: 'high', gap: null })
    expect(staleScenariosForReview(loadProfile()).length).toBe(0)
  })

  it('returns results older than threshold', () => {
    // Manually inject an old result
    const profile = loadProfile()
    profile.domains[1] = {
      domain_name: 'Scripting and Automation',
      results: [{
        scenario_id: 'd01-old',
        title: 'Old Scenario',
        level: 2,
        confidence: 'medium',
        gap: null,
        timestamp: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(), // 30 days ago
      }]
    }
    localStorage.setItem('sysadmin_assessment_profile', JSON.stringify(profile))

    const stale = staleScenariosForReview(loadProfile())
    expect(stale.length).toBe(1)
    expect(stale[0].scenario_id).toBe('d01-old')
  })
})

describe('clearProfile and onboarding', () => {
  beforeEach(() => clearStore())

  it('clearProfile removes all profile data', () => {
    saveResult({ scenario: mkScenario(), level: 2, confidence: 'high', gap: null })
    clearProfile()
    const p = loadProfile()
    expect(p.domains).toEqual({})
  })

  it('onboarding dismissed state persists', () => {
    expect(isOnboardingDismissed()).toBe(false)
    dismissOnboarding()
    expect(isOnboardingDismissed()).toBe(true)
  })
})
