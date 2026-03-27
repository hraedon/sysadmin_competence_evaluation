# CONTENT-02: Some L4 Rubric Findings Test Specific Knowledge, Not Reasoning

## Severity
Low/Medium — framework integrity

## Location
Primary example: `scenarios/d04/audit_the_revocation_test/scenario.yaml` — finding `no_delta_crl_is_a_gap`

## Description
The framework's stated principle is "reasoning over recall" — scenarios should test application of principles, not memorized facts. This principle is not consistently upheld across all rubrics.

**Specific case**: `d04-audit-the-revocation-test`, L4 discriminator. The L3 → L4 transition requires the learner to identify "the absence of delta CRL configuration as the underlying design gap." From `level_indicators.level_4`:

> "identifies the absence of delta CRL configuration as the underlying design gap: without delta CRLs, effective revocation propagation delay equals the full CRL validity period"

A learner who understands conceptually that CRL caching creates a propagation delay window, understands that the window's duration equals the CRL validity period, and understands that there should be a mechanism to reduce this window — but does not know the term "delta CRL" — will be leveled at L3 despite demonstrating correct conceptual reasoning.

Conversely, a learner who has memorized "delta CRL exists to solve CRL caching delays" can reach L4 without understanding *why* the window exists or *how* delta CRLs reduce it.

The artifact explicitly exposes "Delta CRL: Not configured" as a data point — so the finding is not pure recall, it requires connecting the data point to its implication. But the discriminator still rewards knowledge of the specific term over reasoning about the mechanism.

## Remediation

**Audit approach**: Review L4 findings across all scenarios. Flag findings where:
- The discriminator requires naming a specific technology, protocol, or term, and
- A learner who demonstrates correct conceptual reasoning but doesn't know the term would be underscored

**Fix options**:
1. Make the L4 discriminator term-agnostic: "identifies that the environment lacks a mechanism to publish incremental revocation updates on a sub-CRL-validity-period cycle" rather than "identifies absence of delta CRL"
2. Add the term to the scenario artifact as a labeled field the learner is expected to interpret (as this scenario partially does — the artifact shows "Delta CRL: Not configured"), making it a literacy/interpretation task rather than recall
3. Accept the finding as-is but explicitly note in the framework documentation that some L4 discriminators require domain vocabulary fluency, not just reasoning

Option 3 is honest but weakens the "reasoning not recall" claim. Options 1 and 2 preserve the principle.

## Related
EVAL-06 (D14 evaluator variance — similar tension between terminology recognition and reasoning assessment)
