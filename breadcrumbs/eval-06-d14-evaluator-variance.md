# EVAL-06: D14 Theory of Mind — High Expected Evaluator Variance on Subtle Distinctions

## Severity
Medium — evaluation quality / credibility

## Location
`scenarios/d14/` — all four scenarios: audit_the_stressed_stakeholder, audit_the_siloed_upgrade, audit_the_baseline_assumption, audit_the_messenger

## Description
D14 scenarios ask the evaluator to assess social reasoning, stakeholder communication, and organizational dynamics. These are exactly the areas where LLM evaluation is least reliable, for two reasons:

**Subtle level discriminators**: The level distinctions in D14 rubrics depend on the evaluator correctly parsing fine-grained differences in reasoning sophistication. For example, in d14-audit-the-messenger:
- L2: "identifies that James is unhelpful"
- L4: "names the deliberate definitional mechanism James uses to maintain plausible deniability"

That distinction — between identifying that someone is obstructive and identifying *how* they structure their obstruction — is exactly the kind of nuance where evaluator models are expected to show significant variance. A model that pattern-matches on "James is being difficult" without tracking whether the response names the specific mechanism could mis-level in either direction.

**No human-evaluator baseline**: The four D14 scenarios have 100% Sonnet calibration against synthetic responses. There is no data on how the evaluator handles real human responses to these scenarios, and no human-expert comparison to validate that the evaluator's level assignments are meaningful.

For a platform that makes diagnostic claims about organizational reasoning capability, evaluator variance on D14 is not a theoretical concern — it directly affects the reliability of the profile's Domain 14 level assignment.

## Remediation

1. **Ambiguous synthetic responses** (see EVAL-05): Author mixed-signal responses for D14 scenarios specifically, where the response correctly identifies the social dynamic but uses either imprecise language (should this be L3 or L2?) or correct language without the specific mechanism named (should this be L4 or L3?). Run the harness on these.

2. **Inter-run variance check**: Run each D14 scenario's existing synthetic responses through the evaluator 5 times. D14 should show higher variance than D01-D04 (which have concrete technical findings). If level assignments vary across runs for D14, that's a calibration red flag.

3. **Human response pilot**: Before making credibility claims about D14 evaluation, run 5–10 real human responses through the evaluator and have a domain expert manually assign levels. Compare. Any scenario with >30% disagreement between human expert and evaluator should have its rubric and level indicators revised.

## Related
EVAL-05 (calibration synthetic-only), EVAL-02 (almost_caught unused — especially relevant for D14 near-misses)
