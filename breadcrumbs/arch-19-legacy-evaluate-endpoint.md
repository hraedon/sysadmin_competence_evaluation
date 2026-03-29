# ARCH-19: Legacy v1 `/evaluate` Endpoint Still Active

## Severity
Low

## Location
`platform/lab-controller/app/routers/evaluate.py`

## Description
The v1 evaluate API (`POST /evaluate` and `POST /lab/evaluate`) was the pre-ARCH-09 evaluation path. It accepts a full `EvaluateRequest` containing the scenario object (including rubric fields) in the request body and calls the AI directly.

After ARCH-09 completion, the frontend exclusively uses `POST /api/evaluate` (evaluate_v2.py), which loads the rubric server-side. The v1 endpoint is dead from the frontend's perspective but remains registered and accessible to any caller with a valid API key or JWT.

**The risk:** A direct API caller (or a compromised client) can still use v1 to send evaluation requests with arbitrary rubric data, bypassing the server-side rubric validation that ARCH-09 added. This is a lower-level concern than the original SEC-05 issue (rubric in public manifest) but leaves a gap where the server still *accepts* externally-supplied rubric data.

## Remediation
Remove `evaluate.py` and its routes from `main.py` once there are no callers. Verify no external tools or scripts still use `/evaluate` or `/lab/evaluate` before deletion.

## Related
ARCH-09, SEC-05
