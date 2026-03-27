# EVAL-02: almost_caught Field Captured but Never Consumed

## Severity
Low

## Location
Evaluator prompt (in `evaluator.js`), `calibration/run.mjs` (logged only), `platform/frontend/src/App.jsx` and `ScenarioPanel.jsx` (not consumed)

## Description
The evaluator prompt defines `almost_caught` as findings "touched on but not described with enough precision to be fully credited." The calibration harness logs these values. But neither the profile update logic nor any UI element differentiates `almost_caught` findings from fully missed ones — partial credit is not recorded, and the coaching nudge opportunity is unused.

This is a meaningful diagnostic signal being discarded. A learner who nearly identified a critical finding has a different capability profile than one who missed it entirely.

## Remediation

Decide what `almost_caught` should mean in the product before implementing:

1. **Scoring**: Should near-misses contribute partial credit to the level assignment? If so, update the level-determination logic in `evaluator.js`.
2. **Coaching**: Should near-misses trigger a focused coaching nudge in Mode C? ("You were close on X — what specifically would have made that a complete answer?")
3. **Profile display**: Surface near-misses in the results panel with distinct styling (e.g., amber vs. red for fully missed), so the learner sees the distinction.

The data is already there — this is a UI and scoring logic gap, not a data collection problem.

## Related
EVAL-01
