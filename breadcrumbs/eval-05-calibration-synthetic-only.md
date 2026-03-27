# EVAL-05: Calibration Coverage Blind Spot — Synthetic Responses Only

## Severity
Medium — evaluation quality

## Location
`calibration/run.mjs` — all synthetic response files at `scenarios/*/response_level_{1,2,3,4}.txt`

## Description
The calibration harness tests whether the evaluator assigns the correct level to synthetic responses authored to exhibit each level's characteristics. The 100% Sonnet pass rate is a strong signal for rubric quality — it means the rubric's findings and miss signals are well-constructed enough that correctly authored responses land at the intended level.

It is not a signal for evaluator robustness against real-world learner responses.

Synthetic responses are authored to cleanly exhibit each level. Real responses are messy: they may catch some L3 findings and one L4 finding but miss another, use imprecise language that partially matches a finding, address the wrong framing of a finding, or exhibit L4 reasoning depth on an L2 content read. The calibration harness has no test cases for:

- Responses that exhibit mixed signals across levels
- Responses where `almost_caught` should fire (partial credit cases)
- Responses that correctly identify all findings but use L2-level framing
- Responses that use L4-level framing but miss key findings

The harness is also silent on inter-run variance: for any given real response, does the evaluator assign the same level on repeated runs? This is an unverified assumption for local models with non-zero temperature.

## Remediation

1. **Ambiguous synthetic responses**: Author a fifth response class per scenario — "mixed signal" responses that straddle level boundaries — and define the expected outcome. These expose rubric over-crediting and evaluator variance.

2. **Variance testing**: For a sample of scenarios, run the same response through the evaluator 5 times and check if the level assignment is consistent. Flag scenarios with >0 variance in level assignment as calibration concerns.

3. **Human-response baseline**: For any scenario where evaluation reliability is a credibility claim (particularly D14 Theory of Mind), run at least a small set of real human responses through the evaluator and manually verify the output. This is the only way to distinguish rubric quality from evaluation robustness.

## Related
EVAL-02 (almost_caught unused — the partial credit case is the primary gap in calibration coverage), EVAL-06
