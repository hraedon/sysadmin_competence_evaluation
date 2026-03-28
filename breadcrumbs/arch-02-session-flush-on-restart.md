# ARCH-02: Session Flush on Startup Is Too Aggressive

## Severity
Medium

## Location
`platform/lab-controller/app/main.py` — `startup_event()`, line ~132

## Description
On startup, the controller deletes all `LabSession` records unconditionally:

```python
db.query(LabSession).delete()  # Flush sessions on restart as Hyper-V state is unknown
```

If the controller restarts mid-provisioning (crash, OOM kill, rolling deploy), any VM currently being configured is left in a partially-provisioned state. The session record is gone, so the reaper can never tear it down. The environment stays at whatever status it had at crash time ("provisioning") and won't return to "available" unless manually reset or the environments.yaml sync logic happens to overwrite the status.

The comment justification ("Hyper-V state is unknown") is true but the response is too blunt — it conflates "we don't know if this session is still valid" with "we should destroy the record needed to clean it up."

## Remediation

Instead of deleting sessions on startup, mark them as `suspect` (add a status field to `LabSession` or use a separate flag). Let the reaper attempt teardown on any `suspect` session before deleting the record. If teardown succeeds, the environment returns to `available`. If it fails, the environment moves to `faulted` and the record is preserved for investigation.

This ensures the reaper — which already knows how to call `teardown_environment_logic` — handles the cleanup path rather than silently losing the reference.

## Related
ARCH-01, ARCH-03

## Resolution — Session 28 (2026-03-27)

- `load_environments()` no longer calls `db.query(LabSession).delete()`.
- Instead, all surviving sessions are marked `suspect=True` with `expires_at` forced to `utcnow()`.
- Added `suspect` column (Boolean, default False) to `LabSession` model with migration guard (`ALTER TABLE sessions ADD COLUMN suspect BOOLEAN DEFAULT 0`).
- The reaper's existing expired-session collection naturally picks up suspect sessions on its next tick (since their expiry was forced), triggering graceful teardown via the standard `teardown_environment_logic` path.
- This reuses the well-tested teardown code path (VM revert + Guacamole cleanup + session deletion) rather than adding a separate recovery mechanism.
- Test coverage: `test_suspect_sessions_marked_on_startup` in `tests/test_integration.py` verifies the session is marked suspect (not deleted) with forced expiry.
