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

The evaluator's primary calibration signal is what is MISSING (`missed` array),
not reasoning quality. A response with an empty `missed` array will almost always
receive an L4 rating regardless of level indicator prose.

**The most common failure: level inflation (L2 rated L3, or L3 rated L4)**

The synthetic response is catching too many findings — including findings intended
for the next level up. Causes and fixes:

1. Read the evaluator's returned `caught` array. Identify which finding should NOT
   have been caught at this level.
2. Check whether the synthetic response states that finding explicitly. If yes,
   remove it.
3. If the finding is not stated but the evaluator still catches it, the response
   contains content that makes the finding an obvious inference. Identify and remove
   the inference-triggering sentence — not just the explicit claim.
4. As a last resort, restructure the rubric: remove the finding as a separate rubric
   entry and fold it into the level indicator as explicit scope language
   ("Does NOT explain X"). This removes it from the `caught`/`missed` comparison
   entirely.

**The less common failure: level deflation (L3 rated L2)**

The synthetic response is missing a finding it should catch. Check whether the
response actually contains enough specificity for the evaluator to identify the
finding. The fix is usually adding a concrete specific from the artifact (an exact
log message, a field name, a permission entry) rather than general framing.

**A subtler inflation pattern: response quality signals L4 even when a finding is missed**

If the `missed` array is non-empty but the evaluator still returns a higher level,
the response's overall quality is overriding the missed finding signal. This happens
when a lower-level response is *exhaustively* complete on the findings it does cover.
For example: a Level 3 response that correctly lists five NTLM fallback conditions
(all five from the rubric) may read as L4-quality prose even if the L4 finding is
absent. Fix: trim the exhaustive coverage on lower-level findings to match the
level indicator's expected depth — not wrong, just not exhaustive.

**Rubric adjustments**

Adding "Does NOT [L4 criterion]" to the level_3 indicator helps distinguish L3
from L4 when the distinction is about reasoning depth and there is no separate
finding to miss. This is a secondary tool — synthetic response content is the
primary lever.

**Parse failures (`returned: undefined` in the results JSON)**

Occasionally the evaluator returns a response that doesn't parse to a level number.
This appears in results as `deviation: NaN` and `pass: false` with `returned: undefined`.
These are transient API errors, not calibration failures. If a scenario shows a parse
failure in one run but passes cleanly in another, it is not a calibration problem —
re-run the scenario to confirm. If parse failures are frequent, check for API rate
limiting or unusually long responses exceeding context.

See `orchestration_design.md` (Evaluation Quality Control) for the full
calibration procedure.
