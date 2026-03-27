# CONTENT-01: Domain Coverage Heavily Concentrated in D01–D05

## Severity
Medium — credibility / completeness

## Location
`scenarios/` — distribution by domain

## Description
The platform claims to implement a 14-domain comprehensive assessment framework. The actual scenario distribution is heavily concentrated:

| Domain | Count | Notes |
|---|---|---|
| D01 Scripting | 5 | |
| D02 Identity/IAM | 8 | |
| D03 Networking | 5 | |
| D04 Certificates/PKI | 5 | |
| D05 Storage | 5 | |
| D06 Compute | 1 | |
| D07 Cloud Primitives | 2 | |
| D08 Security Reasoning | 1 | |
| D09 Change Management | 4 | |
| D10 Backup/Recovery | 1 | |
| D11 Log Reading | 3 | |
| D12 Linux | 1 | |
| D13 Frameworks as Tools | 3 | |
| D14 Theory of Mind | 4 | |

D06, D08, D10, and D12 have a single scenario each. A single scenario cannot reliably discriminate between L1–L4 on a domain — it tests one context at one difficulty level. A learner who happens to have seen that specific scenario type (RAID degradation, patch compliance, backup job success) gets a distorted profile reading for the entire domain.

For D06, D08, D10, and D12, the profile's domain-level reading is essentially meaningless from a psychometric standpoint — it's a single data point dressed up as a domain assessment.

## Remediation

**Minimum viable coverage**: Each domain needs at least 3 scenarios spanning at least 2 distinct difficulty levels before the domain-level profile reading is informative. Priority order for gap-filling:

1. D10 Backup/Recovery — 1 scenario, no L3/L4 coverage
2. D08 Security Reasoning — 1 scenario
3. D06 Compute Architecture — 1 scenario
4. D12 Linux Administration — 1 scenario

**If publishing or presenting the platform as a comprehensive assessment tool**, either:
- Fill the gaps (2–3 scenarios per undercovered domain), or
- Explicitly scope the credibility claim: "this platform provides strong coverage of D01–D05 and D09; other domains are illustrative"

Claiming 14 domains with 54 scenarios is technically accurate but misleading if 4 domains have 1 scenario each and the profile treats all domains equally in its aggregation logic.

## Related
EVAL-03 (profile aggregation logic — domain levels based on median across scenarios; single-scenario domains give misleadingly precise-looking readings)
