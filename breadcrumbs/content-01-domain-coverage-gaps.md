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
| **D06 Compute** | **3** | **Expanded** — added audit_the_noisy_neighbor (L2), audit_the_boot_failure (L3) |
| D07 Cloud Primitives | 3 | |
| **D08 Security Reasoning** | **3** | Was 2; added audit_the_certificate_expiration_trap |
| D09 Change Management | 4 | |
| **D10 Backup/Recovery** | **3** | Was 2; added audit_the_replication_that_wasnt |
| D11 Log Reading | 3 | |
| D12 Linux | 3 | Was 1; added audit_the_exit_trap, audit_the_status_trap |
| D13 Frameworks as Tools | 2 | |
| D14 Theory of Mind | 5 | Was 4; added audit_the_taxonomy_gap |

**Total: 58 scenarios** (d01-d14) + 20 d15 scenarios (synced from agentic-onboarding) = 78 total.

D06 now meets the 3-scenario minimum. D08 (2) and D10 (2) remain below the threshold. D13 (2) is a synthesis domain where 2 is somewhat more defensible.

## Remediation

**Minimum viable coverage**: Each domain needs at least 3 scenarios spanning at least 2 distinct difficulty levels before the domain-level profile reading is informative. All domains now meet the 3-scenario minimum except D13 (synthesis domain, 2 is defensible).

D06, D08, D10, and D12 have all been expanded to 3 scenarios. D13 (2 scenarios) remains below threshold but is a synthesis domain where 2 is somewhat more defensible.

**If publishing or presenting the platform as a comprehensive assessment tool**, either:
- Fill the gaps (1–2 more scenarios for D06, D08, D10), or
- Explicitly scope the credibility claim: "D06 coverage is illustrative, not diagnostic"

D13 (2 scenarios) is also below the threshold but is a synthesis domain where single-scenario assessment is somewhat more defensible.

## Related
EVAL-03 (profile aggregation logic — domain levels based on median across scenarios; single-scenario domains give misleadingly precise-looking readings)
