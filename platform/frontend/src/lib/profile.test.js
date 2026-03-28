/**
 * Unit tests for profile.js — localStorage-backed capability profile.
 *
 * Run with: node --test platform/frontend/src/lib/profile.test.js
 * Requires Node 18+. No additional test runner needed.
 *
 * Tests cover: saveResult aggregation, domainLevel median logic,
 * recommendNext sequencing, staleScenariosForReview threshold,
 * and almost_caught persistence.
 */

import { test, describe, beforeEach } from 'node:test'
import assert from 'node:assert/strict'

// ── localStorage shim for Node ──────────────────────────────────────────
const store = {}
globalThis.localStorage = {
  getItem: (k) => store[k] ?? null,
  setItem: (k, v) => { store[k] = String(v) },
  removeItem: (k) => { delete store[k] },
  clear: () => { for (const k of Object.keys(store)) delete store[k] },
}

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
  beforeEach(() => localStorage.clear())

  test('returns empty profile when localStorage is empty', () => {
    const p = loadProfile()
    assert.deepStrictEqual(p.domains, {})
    assert.strictEqual(p.updated, null)
  })

  test('returns empty profile when localStorage contains invalid JSON', () => {
    localStorage.setItem('sysadmin_assessment_profile', 'not json')
    const p = loadProfile()
    assert.deepStrictEqual(p.domains, {})
  })
})

describe('saveResult', () => {
  beforeEach(() => localStorage.clear())

  test('creates domain entry on first save', () => {
    const s = mkScenario()
    const p = saveResult({ scenario: s, level: 2, confidence: 'high', gap: null })
    assert.strictEqual(p.domains[1].domain_name, 'Scripting and Automation')
    assert.strictEqual(p.domains[1].results.length, 1)
    assert.strictEqual(p.domains[1].results[0].level, 2)
  })

  test('replaces prior result for same scenario_id', () => {
    const s = mkScenario()
    saveResult({ scenario: s, level: 1, confidence: 'low', gap: 'missed everything' })
    const p = saveResult({ scenario: s, level: 3, confidence: 'high', gap: null })
    assert.strictEqual(p.domains[1].results.length, 1)
    assert.strictEqual(p.domains[1].results[0].level, 3)
  })

  test('preserves results from different scenarios in same domain', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 2, confidence: 'medium', gap: null })
    const p = saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'high', gap: null })
    assert.strictEqual(p.domains[1].results.length, 2)
  })

  test('persists gap field', () => {
    const p = saveResult({ scenario: mkScenario(), level: 2, confidence: 'medium', gap: 'needs error handling' })
    assert.strictEqual(p.domains[1].results[0].gap, 'needs error handling')
  })

  test('persists almost_caught field', () => {
    const p = saveResult({
      scenario: mkScenario(),
      level: 2,
      confidence: 'medium',
      gap: null,
      almost_caught: ['finding_a', 'finding_b'],
    })
    assert.deepStrictEqual(p.domains[1].results[0].almost_caught, ['finding_a', 'finding_b'])
  })

  test('defaults almost_caught to empty array when omitted', () => {
    const p = saveResult({ scenario: mkScenario(), level: 2, confidence: 'high', gap: null })
    assert.deepStrictEqual(p.domains[1].results[0].almost_caught, [])
  })

  test('round-trips through localStorage', () => {
    saveResult({ scenario: mkScenario(), level: 3, confidence: 'high', gap: 'a gap' })
    const reloaded = loadProfile()
    assert.strictEqual(reloaded.domains[1].results[0].level, 3)
    assert.strictEqual(reloaded.domains[1].results[0].gap, 'a gap')
  })
})

describe('domainLevel — median logic', () => {
  beforeEach(() => localStorage.clear())

  test('returns null for empty domain', () => {
    assert.strictEqual(domainLevel(loadProfile(), 1), null)
  })

  test('returns the single result level', () => {
    saveResult({ scenario: mkScenario(), level: 3, confidence: 'high', gap: null })
    assert.strictEqual(domainLevel(loadProfile(), 1), 3)
  })

  test('returns median of odd count', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 1, confidence: 'low', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-c' }), level: 4, confidence: 'high', gap: null })
    assert.strictEqual(domainLevel(loadProfile(), 1), 3)
  })

  test('returns floor of average for even count', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 2, confidence: 'medium', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'medium', gap: null })
    // (2+3)/2 = 2.5 → floor → 2
    assert.strictEqual(domainLevel(loadProfile(), 1), 2)
  })

  test('handles single outlier without dragging median', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-b' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-c' }), level: 1, confidence: 'low', gap: null })
    assert.strictEqual(domainLevel(loadProfile(), 1), 3)
  })
})

describe('recommendNext', () => {
  beforeEach(() => localStorage.clear())

  const scenarios = [
    mkScenario({ id: 'd01-a', level: 1, difficulty: 2 }),
    mkScenario({ id: 'd01-b', level: 2, difficulty: 3 }),
    mkScenario({ id: 'd01-c', level: 3, difficulty: 4 }),
    mkScenario({ id: 'd01-d', level: 3, difficulty: 5 }),
  ]

  test('returns lowest-difficulty scenario when no prior results', () => {
    const next = recommendNext(scenarios, loadProfile(), 1)
    assert.strictEqual(next.id, 'd01-a')
  })

  test('recommends next level up after assessment', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 1, confidence: 'medium', gap: null })
    const next = recommendNext(scenarios, loadProfile(), 1)
    assert.strictEqual(next.id, 'd01-b')
  })

  test('returns null when all scenarios completed', () => {
    for (const s of scenarios) {
      saveResult({ scenario: s, level: s.level, confidence: 'high', gap: null })
    }
    const next = recommendNext(scenarios, loadProfile(), 1)
    assert.strictEqual(next, null)
  })

  test('falls back to same-level scenario if next level not available', () => {
    saveResult({ scenario: mkScenario({ id: 'd01-c' }), level: 3, confidence: 'high', gap: null })
    saveResult({ scenario: mkScenario({ id: 'd01-a' }), level: 1, confidence: 'low', gap: null })
    // median of [1,3] = floor(2) = 2 → looks for L3, finds d01-d
    const next = recommendNext(scenarios, loadProfile(), 1)
    // assessed = 2, target = 3, d01-c already done → d01-d is L3 and available
    assert.strictEqual(next.id, 'd01-d')
  })
})

describe('staleScenariosForReview', () => {
  beforeEach(() => localStorage.clear())

  test('returns empty for fresh results', () => {
    saveResult({ scenario: mkScenario(), level: 2, confidence: 'high', gap: null })
    assert.strictEqual(staleScenariosForReview(loadProfile()).length, 0)
  })

  test('returns results older than threshold', () => {
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
    assert.strictEqual(stale.length, 1)
    assert.strictEqual(stale[0].scenario_id, 'd01-old')
  })
})

describe('clearProfile and onboarding', () => {
  beforeEach(() => localStorage.clear())

  test('clearProfile removes all profile data', () => {
    saveResult({ scenario: mkScenario(), level: 2, confidence: 'high', gap: null })
    clearProfile()
    const p = loadProfile()
    assert.deepStrictEqual(p.domains, {})
  })

  test('onboarding dismissed state persists', () => {
    assert.strictEqual(isOnboardingDismissed(), false)
    dismissOnboarding()
    assert.strictEqual(isOnboardingDismissed(), true)
  })
})
