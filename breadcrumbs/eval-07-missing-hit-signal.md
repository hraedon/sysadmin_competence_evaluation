# EVAL-07: Missing "Hit Signal" in Rubric Schema

## Severity
Low/Medium

## Location
`scenario_specification_v2.md`
`core/evaluator.js`

## Description
The current rubric schema provides a `miss_signal` to help the AI identify when a finding is *not* present. However, it lacks an explicit `hit_signal` (positive evidence).

In messy, complex, or multi-faceted responses, the AI can sometimes become confused by "almost correct" terminology or tangential reasoning. A `hit_signal` would provide the AI with specific keywords, logic patterns, or evidence that *must* be present to credit the finding.

Example:
- `id`: credential_in_log
- `miss_signal`: "Candidate asks only functional questions about AD permissions."
- `hit_signal`: "Candidate specifically names the $newPassword variable being passed to Write-OperationLog."

## Remediation
Update the V2.0 schema to include an optional `hit_signal` field for findings. Update `evaluator.js` to include this field in the system prompt block for each finding.

## Related
CONTENT-02 (Recall disguised as reasoning).
