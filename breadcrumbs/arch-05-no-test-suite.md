# ARCH-05: No Automated Test Coverage

## Severity
Low (now), Medium (as platform matures)

## Location
Repo-wide — no test files exist outside `node_modules`

## Description
The codebase has zero unit or integration tests. The calibration harness tests AI evaluation quality, not code correctness. Logic with real failure modes has no coverage:

- `sanitize_scenario_id` and `resolve_scenario_path` — the path traversal guard. A regression here is a directory traversal vulnerability.
- The atomic environment selection in `main.py` — the affected-rows guard that prevents double-provisioning.
- `buildSystemPrompt` in `evaluator.js` — field inclusion/exclusion logic. A regression that accidentally includes `learning_note` would leak answers.
- JSON parse fallback in `evaluate()` — the retry path and null-parse handling (see EVAL-01).
- `profile.js` domain level aggregation and `recommendNext` logic — affects the learner experience directly.

The calibration harness catches evaluator *quality* regressions. It won't catch a broken `sanitize_scenario_id` regex or a `buildSystemPrompt` that starts including rubric fields it shouldn't.

## Remediation

Start narrow — test the highest-consequence logic first:

1. **Path traversal guard** (`sanitize_scenario_id`, `resolve_scenario_path`): pytest parametrized test with traversal payloads (`../`, `%2e%2e`, absolute paths). These are the highest-consequence functions to have coverage on.
2. **buildSystemPrompt field exclusion**: Jest test asserting that `learning_note` and rubric `description` fields are absent from the assembled prompt string.
3. **profile.js**: Jest tests for `domainLevel` aggregation, `recommendNext` filtering, and `staleScenariosForReview` timing logic.

The calibration harness can remain as the AI quality gate. Code-level tests cover the deterministic logic the harness doesn't exercise.

## Related
SEC-05 (buildSystemPrompt field leakage would be caught by tests)
