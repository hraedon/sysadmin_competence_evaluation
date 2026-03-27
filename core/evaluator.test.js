/**
 * Unit tests for evaluator.js — deterministic logic only.
 *
 * Run with: node --test core/evaluator.test.js
 * Requires Node 18+. No additional test runner needed.
 *
 * These tests cover the field-inclusion/exclusion logic in buildSystemPrompt,
 * which is the highest-consequence deterministic path: a regression that
 * accidentally includes learning_note would leak answers to the AI evaluator.
 */

import { test, describe } from 'node:test'
import assert from 'node:assert/strict'
import { buildSystemPrompt } from './evaluator.js'

// Minimal V2 scenario fixture with both protected and public fields
const scenario = {
  schema_version: 2.0,
  domain_name: 'Scripting and Automation',
  level: 2,
  title: 'Test Scenario',
  presentation: {
    modes: {
      A: {
        type: 'script',
        context: 'Review the following script.',
      },
    },
  },
  rubric: {
    findings: [
      {
        id: 'missing_error_handling',
        type: 'critical',
        description: 'The script does not handle the case where the file is missing.',
        miss_signal: 'A response that does not mention error handling or exceptions.',
        learning_note: 'Always wrap file operations in try/catch blocks to handle IO errors.',
      },
      {
        id: 'hardcoded_path',
        type: 'secondary',
        description: 'The file path is hardcoded rather than parameterised.',
        miss_signal: 'A response that does not flag the hardcoded path as a maintenance concern.',
        learning_note: 'Use parameters or config files so paths can be changed without editing the script.',
      },
    ],
    level_indicators: {
      level_1: 'Identifies no findings.',
      level_2: 'Identifies the critical finding only.',
      level_3: 'Identifies both findings with correct severity.',
      level_4: 'Identifies both findings and proposes concrete fixes.',
    },
  },
}

describe('buildSystemPrompt — field exclusion', () => {
  test('learning_note is never included in the prompt', () => {
    const prompt = buildSystemPrompt(scenario, 'some artifact content')
    assert.ok(!prompt.includes('try/catch blocks'), 'learning_note content must not appear in the prompt')
    assert.ok(!prompt.includes('learning_note'), 'the key "learning_note" must not appear in the prompt')
    assert.ok(!prompt.includes('parameters or config files'), 'second learning_note content must not appear')
  })

  test('miss_signal is included by default (standard rubric)', () => {
    const prompt = buildSystemPrompt(scenario, 'some artifact content')
    assert.ok(prompt.includes('WATCH FOR (MISS SIGNAL)'), 'miss_signal block must appear in standard mode')
    assert.ok(prompt.includes('does not mention error handling'), 'miss_signal content must appear')
  })

  test('miss_signal is excluded when compactRubric=true', () => {
    const prompt = buildSystemPrompt(scenario, 'some artifact content', { compactRubric: true })
    assert.ok(!prompt.includes('WATCH FOR (MISS SIGNAL)'), 'miss_signal block must not appear in compact mode')
    assert.ok(!prompt.includes('does not mention error handling'), 'miss_signal content must not appear in compact mode')
  })

  test('finding descriptions are always included', () => {
    const prompt = buildSystemPrompt(scenario, 'some artifact content', { compactRubric: true })
    assert.ok(prompt.includes('does not handle the case where the file is missing'), 'critical finding description must appear')
    assert.ok(prompt.includes('hardcoded rather than parameterised'), 'secondary finding description must appear')
  })

  test('level_indicators are always included', () => {
    const prompt = buildSystemPrompt(scenario, 'some artifact content')
    assert.ok(prompt.includes('Identifies both findings and proposes concrete fixes'), 'level_4 indicator must appear')
    assert.ok(prompt.includes('Identifies no findings'), 'level_1 indicator must appear')
  })

  test('learning_note is excluded even in compactRubric=false mode', () => {
    // Belt-and-suspenders: confirm the exclusion is unconditional, not tied to compactRubric
    const promptFull = buildSystemPrompt(scenario, null, { compactRubric: false })
    const promptCompact = buildSystemPrompt(scenario, null, { compactRubric: true })
    for (const prompt of [promptFull, promptCompact]) {
      assert.ok(!prompt.includes('try/catch blocks'), 'learning_note must not appear in any mode')
    }
  })
})

describe('buildSystemPrompt — V1 schema compatibility', () => {
  const v1scenario = {
    schema_version: 1.0,
    domain_name: 'Networking',
    level: 1,
    title: 'V1 Test',
    delivery_mode: 'A',
    presentation: {
      type: 'log',
      context: 'Analyse this log.',
    },
    rubric: {
      critical_findings: [
        {
          id: 'v1_finding',
          severity: 'critical',
          description: 'A critical V1 finding.',
          miss_signal: 'Misses the V1 critical finding.',
          learning_note: 'This learning note must not appear.',
        },
      ],
      secondary_findings: [],
      level_indicators: {
        level_1: 'Identifies nothing.',
        level_4: 'Identifies all V1 findings.',
      },
    },
  }

  test('V1 schema: learning_note excluded', () => {
    const prompt = buildSystemPrompt(v1scenario, 'log content')
    assert.ok(!prompt.includes('This learning note must not appear'), 'V1 learning_note must not appear')
  })

  test('V1 schema: critical findings included', () => {
    const prompt = buildSystemPrompt(v1scenario, 'log content')
    assert.ok(prompt.includes('A critical V1 finding'), 'V1 finding description must appear')
  })
})

describe('buildSystemPrompt — coach mode fields', () => {
  test('coach_question field appears in JSON schema for coachRound=0', () => {
    const prompt = buildSystemPrompt(scenario, 'artifact', { coachMode: true, coachRound: 0 })
    assert.ok(prompt.includes('coach_question'), 'coach_question must appear in schema for round 0')
  })

  test('resolved field appears in JSON schema for coachRound>0', () => {
    const prompt = buildSystemPrompt(scenario, 'artifact', { coachMode: true, coachRound: 1 })
    assert.ok(prompt.includes('"resolved"'), 'resolved field must appear in schema for follow-up rounds')
  })

  test('no coach fields appear when coachMode=false', () => {
    const prompt = buildSystemPrompt(scenario, 'artifact', { coachMode: false })
    assert.ok(!prompt.includes('COACH MODE'), 'COACH MODE instruction must not appear in standard mode')
    assert.ok(!prompt.includes('"resolved"'), 'resolved field must not appear in standard mode')
  })
})
