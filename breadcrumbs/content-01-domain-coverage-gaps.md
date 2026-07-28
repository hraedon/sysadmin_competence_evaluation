# CONTENT-01: Domain Coverage Heavily Concentrated in D01–D05

## Severity
Medium — credibility / completeness

## Status
**CLOSED (2026-07-28).** All domains d01–d14 now meet the 3-scenario minimum.
D13 was the last gap (2 scenarios); `the_cloud_backup_proposal` (L3 design-review
synthesis) brought it to 3. New domains d16–d18 carry one pilot scenario each by
design (Plan 001 pre-kickoff note #3: pilot early, calibrate the rubric pattern
before authoring full sets); their full scenario sets are tracked by Plan 001
Phase 1, not by this breadcrumb. Calibration of the pilots against real API keys
remains outstanding (see WI-005 history).

## Location
`scenarios/` — distribution by domain

## Description
The platform claims to implement a comprehensive assessment framework. Scenario
distribution as of 2026-07-28:

| Domain | Count | Notes |
|---|---|---|
| D01 Scripting | 6 | |
| D02 Identity/IAM | 8 | |
| D03 Networking | 6 | |
| D04 Certificates/PKI | 6 | |
| D05 Storage | 5 | |
| D06 Compute | 3 | |
| D07 Cloud Primitives | 3 | |
| D08 Security Reasoning | 3 | |
| D09 Change Management | 4 | |
| D10 Backup/Recovery | 3 | |
| D11 Log Reading | 3 | |
| D12 Linux | 3 | |
| D13 Frameworks as Tools | 3 | Was 2; added the_cloud_backup_proposal 2026-07-28 |
| D14 Theory of Mind | 5 | |
| D15 Directing AI Agents | 20 | Synced from agentic-onboarding |
| D16 Observability | 1 | Pilot (alert_fatigue_audit) |
| D17 MV DevOps | 1 | Pilot (the_diff_before_applying) |
| D18 MV Database | 1 | Pilot (the_database_that_filled_the_disk) |

**Total: 84 scenarios** (61 d01–d14 + 20 d15 + 3 pilots). All d01–d14 domains
meet the 3-scenario minimum spanning at least 2 difficulty levels.

## Remediation history

- D06, D08, D10, D12, D14 expanded to minimum in earlier sessions (WI-001).
- D13 third scenario added 2026-07-28 (d13-the-cloud-backup-proposal).
- D16–D18 pilot scenarios added 2026-07-28 per Plan 001 pre-kickoff note #3.

## Related
EVAL-03 (profile aggregation logic — domain levels based on median across scenarios; single-scenario domains give misleadingly precise-looking readings). Note: EVAL-03 now applies to d16–d18 until their full scenario sets land.
