# CONTENT-01: Domain Coverage Heavily Concentrated in D01–D05

## Severity
Medium — credibility / completeness

## Location
`scenarios/` — distribution by domain

## Description
The platform claims to implement a 14-domain comprehensive assessment framework. The actual scenario distribution is heavily concentrated:

| Domain | Count | Notes |
|---|---|---|
| D01 Scripting | 6 | |
| D02 Identity/IAM | 8 | |
| D03 Networking | 6 | |
| D04 Certificates/PKI | 6 | |
| D05 Storage | 5 | |
| **D06 Compute** | **1** | **Still single-scenario** |
| D07 Cloud Primitives | 3 | |
| D08 Security Reasoning | 2 | Was 1; added commission_jit_access_spec |
| D09 Change Management | 4 | |
| D10 Backup/Recovery | 2 | Was 1; added audit_the_identity_trap |
| D11 Log Reading | 3 | |
| D12 Linux | 3 | Was 1; added audit_the_exit_trap, audit_the_status_trap |
| D13 Frameworks as Tools | 2 | |
| D14 Theory of Mind | 5 | Was 4; added audit_the_taxonomy_gap |

**Total: 56 scenarios** (55 web + 1 lab).

D06 is the only remaining single-scenario domain. D08, D10, and D12 have been expanded since the original audit. A single scenario cannot reliably discriminate between L1–L4 — it tests one context at one difficulty level.

For D06, the profile's domain-level reading is essentially meaningless from a psychometric standpoint — it's a single data point dressed up as a domain assessment.

## Remediation

**Minimum viable coverage**: Each domain needs at least 3 scenarios spanning at least 2 distinct difficulty levels before the domain-level profile reading is informative. Remaining gap:

1. **D06 Compute Architecture — 1 scenario.** This is the last single-scenario domain.

D08 (2), D10 (2), and D12 (3) have been expanded. D12 now meets the 3-scenario minimum. D08 and D10 have 2 each — better but still below the 3-scenario threshold for reliable discrimination.

**If publishing or presenting the platform as a comprehensive assessment tool**, either:
- Fill the gaps (1–2 more scenarios for D06, D08, D10), or
- Explicitly scope the credibility claim: "D06 coverage is illustrative, not diagnostic"

D13 (2 scenarios) is also below the threshold but is a synthesis domain where single-scenario assessment is somewhat more defensible.

## Related
EVAL-03 (profile aggregation logic — domain levels based on median across scenarios; single-scenario domains give misleadingly precise-looking readings)
