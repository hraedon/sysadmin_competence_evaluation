# ~~TEST-02~~: Missing High-Value Tests — **Closed**

## Status
- **Resolved**: 2026-04-03
- T-9 (`TestProvisioningFlowExecution`) added to `test_integration.py` — 10 tests, all passing.
- Priorities 1–4, 6, 7 addressed. Priority 5 (concurrent step tracking) deferred as it requires a more complex setup and the WAL-mode fix already protects the invariant.

## Severity (original)
Medium (collectively High — these are the tests that would have caught the bugs that caused the most operational pain)

## Context

The test suite (109 Python + 11 JS + 22 JS profile = 142 tests) has strong coverage of:
- Database models, migrations, session_scope behavior
- Status update helpers, faulted-env recovery, reconciler logic
- Security (path traversal, scenario ID sanitization)
- Auth (JWT, registration, password hashing)
- Evaluation (rubric loading, recording, cross-language consistency)
- Profile (CRUD, import/merge)
- Verification output parsing

What's missing is **the provisioning flow itself** — the code path that caused the most bugs in Sessions 26 and 29. The existing `TestProvisioningFlow` class tests the atomic mutex and capability matching, but not the actual `run_provisioning_flow()` or `run_provisioning_with_watchdog()` execution. Every bug in the list below was discovered manually in production.

## Missing Tests — Prioritized by Bug History

### Priority 1: Provisioning flow error propagation
**Bug it would have caught:** S26 bug #2 — `wait_for_guest_readiness` returned `False` but provisioning continued silently, marking the environment "busy" when nothing was ready.

**Test:** Call `run_provisioning_flow()` with a mock orchestrator where `revert_to_checkpoint` returns `success=False`. Assert the environment transitions to `faulted` (not `busy`). Repeat for `start_vm` failure and `wait_for_guest_readiness` returning `False`. Each orchestrator step failure should raise and the except block should fault the environment.

```python
# Sketch:
async def test_provisioning_faults_on_revert_failure(seeded_db):
    mock_orch = AsyncMock()
    mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(
        success=False, output="", error="Revert failed"
    )
    # ... patch orchestrator, call run_provisioning_flow ...
    # Assert env.status == "faulted" and env.last_error contains "Revert failed"
```

Why this matters: the entire provisioning flow is `await` calls to the orchestrator with `if not res.success: raise`. If someone refactors that logic and drops a check, this test catches it. The S26 bug was exactly this — the check wasn't there at all.

### Priority 2: Guacamole RDP parameter construction (domain\username splitting)
**Bug it would have caught:** S29 bug #3 — `domain\username` passed as a single string to Guacamole's FreeRDP, causing "Log in failed" loop.

**Test:** In `run_provisioning_flow`, after the `creating_guac` step, assert that when `settings.hyperv_guest_username` is `"ad.labdomain.dev\\claude"`, the params dict passed to `guac_client.create_connection` has `username="claude"` and `domain="ad.labdomain.dev"` as separate fields. Also test the case where the username has no backslash (should pass as-is with no domain field).

```python
# Sketch:
async def test_domain_username_split_for_rdp(seeded_db):
    mock_settings.hyperv_guest_username = "ad.labdomain.dev\\claude"
    # ... run provisioning flow to the guac step ...
    call_args = mock_guac.create_connection.call_args
    params = call_args[0][2]  # third positional arg
    assert params["username"] == "claude"
    assert params["domain"] == "ad.labdomain.dev"
```

Why this matters: this is the kind of string-splitting logic that's easy to break in a refactor and impossible to catch without either a unit test or a real RDP connection. The fix in S29 was a 3-line change; the debugging took over an hour because the symptom (Guacamole login loop) didn't obviously point to the credential format.

### Priority 3: Provisioning watchdog triggers teardown
**Bug it would have caught:** S26 bug #2 (partial) — before the watchdog existed, hung provisioning locked environments permanently. After the watchdog was added (S27), its behavior still needs testing.

**Test:** Call `run_provisioning_with_watchdog()` with a mock orchestrator whose `revert_to_checkpoint` blocks for longer than `settings.provisioning_timeout_seconds`. Assert that after the timeout, `teardown_environment_logic` is called (the env is reverted/stopped, not left running), and the environment transitions to `faulted` with a timeout error message.

```python
# Sketch:
async def test_watchdog_triggers_teardown_on_timeout(seeded_db):
    mock_settings.provisioning_timeout_seconds = 1  # 1 second timeout
    mock_orch.revert_to_checkpoint = AsyncMock(side_effect=asyncio.sleep(10))
    # ... call run_provisioning_with_watchdog ...
    # Assert env.status == "faulted" and "timed out" in env.last_error
```

Why this matters: a broken watchdog means a hung provisioning flow permanently locks an environment. The watchdog is the safety net for everything else in the provisioning path.

### Priority 4: `load_environments` preserves busy environment status
**Bug it would have caught:** S29 bug #7 — `load_environments` reset `busy` environments to `available` on restart, which then triggered ARCH-23 (reconciler killed active sessions).

**Test:** Seed DB with one environment at status `"busy"` and one active session. Call `load_environments()`. Assert the environment is still `"busy"` (not reset to `"available"`). Assert the session is marked `suspect` but still exists.

This test *almost* existed — `test_suspect_sessions_marked_on_startup` tested the session marking but had the wrong assertion on `expires_at` (the stale test fixed this session). There was no test for the environment status preservation, which was the actual bug.

```python
# Sketch:
async def test_busy_env_preserved_across_restart(seeded_db):
    # Set env to busy with an active session
    # Call load_environments()
    # Assert env.status == "busy" (NOT "available")
```

### Priority 5: Provisioning step tracking produces observable state
**Bug it would have caught:** S26 bug #1 — progress bar frozen because SQLite locking blocked the polling endpoint from reading step updates.

**Test:** Call `run_provisioning_flow()` with a mock orchestrator that has controllable delays. After each major step completes, read the environment's `provision_step` from the DB *using a separate session* (simulating the polling endpoint). Assert the step value matches the expected stage. This tests that step updates are actually committed and readable by concurrent readers.

This is harder to test correctly because the real bug was about SQLite's journal mode, which is now WAL. But the test still has value: it verifies that `update_provision_step()` commits immediately (not at the end of a long transaction), which is the invariant that the WAL fix relies on.

### Priority 6: Teardown resilience (Guacamole failure doesn't prevent VM revert)
**Bug class:** Not a specific historical bug, but the teardown path has explicit `try/except` blocks around Guacamole operations because they're non-critical — the important thing is that VMs get reverted. A refactor that accidentally makes Guacamole failure abort the teardown would leave VMs running.

**Test:** Call `teardown_environment_logic()` with a mock `guac_client` that raises on `delete_connection`. Assert that VM revert still happens and the environment transitions to `available` (not stuck in `teardown`).

The existing `test_teardown_deletes_session_even_on_revert_failure` tests the inverse (revert fails, session still deleted). This complements it.

### Priority 7: Reaper does not reap suspect sessions with future expiry
**Bug it would have caught:** S29 bug #6 — the original ARCH-02 fix forced `expires_at = now()` on all sessions at restart, causing the reaper to kill them within 60 seconds. The fix was to stop touching `expires_at`. But there's no test that the reaper specifically leaves suspect-but-not-expired sessions alone.

**Test:** Create a session with `suspect=True` and `expires_at` 1 hour in the future. Run the reaper. Assert the session still exists.

## Location
`platform/lab-controller/tests/test_integration.py` — new test class `TestProvisioningFlowExecution` (T-9)

## Implementation Notes
- All tests should use the existing `seeded_db` fixture pattern with `patch.object(main_mod, ...)`.
- The mock orchestrator for provisioning tests needs more methods mocked than the reconciler tests (which only use `get_vm_state` and `revert_to_checkpoint`). Consider a `provisioning_mock_orch` fixture that returns success for all operations by default, with individual tests overriding specific methods to fail.
- Tests 1–3 are the highest value. They test the provisioning flow's error handling, which is where all the S26/S29 production bugs lived.
- Tests 4 and 7 test lifecycle invariants that protect against regression of specific bugs that were painful to diagnose.
- Test 5 is the hardest to write correctly (concurrent session access) but tests the exact failure mode that caused the frozen progress bar.

## Related
TEST-01 (general testing gaps), ARCH-03 (watchdog), ARCH-22 (PSSession fix), ARCH-23 (shared-VM orphan)
