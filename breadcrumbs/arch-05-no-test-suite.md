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

## Partial Resolution — Session 25 (2026-03-27)

Two test files added:

- `platform/lab-controller/tests/test_security.py` — pytest suite for `sanitize_scenario_id` (valid IDs, traversal payloads, encoding bypasses, special characters) and `resolve_scenario_path` (containment check). Run: `pytest platform/lab-controller/tests/test_security.py`

- `core/evaluator.test.js` — Node built-in test runner (`node --test`) suite for `buildSystemPrompt` field inclusion/exclusion: `learning_note` never appears, `miss_signal` appears in standard mode and is absent in `compactRubric=true`, `level_indicators` always present, coach mode JSON schema fields. Covers V1 and V2 schema scenarios.

Remaining coverage gaps: `profile.js` domain aggregation and `recommendNext`, JSON parse fallback in `evaluate()`, atomic environment selection in `main.py`.

## Further Resolution — Session 27 (2026-03-28)

- `platform/frontend/src/lib/profile.test.js` — Node built-in test runner suite (22 tests). Covers: `loadProfile` empty/corrupt state, `saveResult` creation/replacement/round-trip, `almost_caught` persistence, `domainLevel` median logic (odd/even/outlier), `recommendNext` sequencing, `staleScenariosForReview` threshold, `clearProfile`, onboarding state.

## Further Resolution — Session 28 (2026-03-27)

- `platform/lab-controller/tests/test_integration.py` — pytest suite (19 tests). Covers:
  - **Database (5):** Model fields, suspect flag (ARCH-02), session_scope commit/rollback.
  - **Helpers (2):** `_update_provision_step`, `_update_env_status`.
  - **Provisioning (3):** Atomic mutex claim/reject, capability matching.
  - **Teardown/Reaper (5):** Revert + mark available, session deletion on failure, Guacamole connection cleanup, ARCH-02 suspect session marking, reaper expired collection.
  - **Evaluator (4):** Python-side `build_system_prompt` field exclusion (learning_note, miss_signal, compact mode, level_indicators).
- Added `app/__init__.py` to make the app directory a proper Python package (needed for `mock.patch` resolution).

**Total test count: 72** (20 security + 19 integration + 11 JS evaluator + 22 JS profile). All passing.

**Remaining gaps:** Frontend component tests (Vitest + React Testing Library), JSON parse fallback in `evaluate()`.
