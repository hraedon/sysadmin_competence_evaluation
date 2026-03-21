# Calibration Harness

Tests the AI evaluator against synthetic responses to verify level estimates match
expected calibration before exposing the platform to real learners.

## Usage

```bash
cd calibration
npm install

# Run all scenarios
ANTHROPIC_API_KEY=sk-ant-... node run.mjs

# Run a single scenario
ANTHROPIC_API_KEY=sk-ant-... node run.mjs --scenario d01-audit-ai-gave-you-this

# Run a single domain
ANTHROPIC_API_KEY=sk-ant-... node run.mjs --domain 1
```

Exit code 0 = all calibrated scenarios passed. Exit code 1 = one or more failures.
Results JSON written to `results/calibration_YYYY-MM-DDTHH-MM-SS.json`.

## Pass/fail criteria

A run passes if the evaluator's returned level matches the expected level
(i.e., the filename `response_level_N.txt` expects level N). The tolerance
is ±0.5 — an exact match is a clean pass.

Scenarios with 2 or more level mismatches are flagged as having systematic
calibration issues. The recommended action is to adjust `miss_signal` specificity
in the scenario rubric until the evaluator returns the correct level consistently.

## Synthetic response files

Each scenario directory contains `response_level_1.txt` through
`response_level_4.txt`. These are synthetic responses designed to exhibit
the reasoning posture described in the scenario's `level_indicators`.

Level 1 responses specifically exhibit the `miss_signal` failure mode described
in the critical findings — they demonstrate the specific wrong reasoning the
rubric is trying to detect, not merely an incomplete answer.

## What to do when calibration fails

1. Read the failing scenario's level indicators again carefully.
2. Read the failing synthetic response.
3. Read the evaluator's returned JSON (in the results file) — specifically
   the `caught`, `missed`, and `gap` fields.
4. If the evaluator is catching findings it shouldn't (false positives at L1):
   the L1 synthetic response is too complete — revise it to more specifically
   exhibit the miss_signal.
5. If the evaluator is missing findings it should catch (false negatives at L3/L4):
   the rubric's miss_signal may be too vague — add specificity to help the
   evaluator distinguish L2 from L3 reasoning in that scenario.
6. Re-run after adjusting. Repeat until consistent.

See `orchestration_design.md` (Evaluation Quality Control) for the full
calibration procedure.
