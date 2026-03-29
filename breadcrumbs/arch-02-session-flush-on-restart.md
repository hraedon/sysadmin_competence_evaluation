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

## Resolution — Session 28 (2026-03-27) + correction Session 29 (2026-03-29)

**Session 28 (commit prior to c0ae237):** `load_environments()` no longer calls `db.query(LabSession).delete()`. Sessions marked `suspect=True` and `expires_at` forced to `utcnow()`. Added `suspect` column.

**Bug in Session 28 fix (discovered Session 29):** The forced-expiry approach was too aggressive — the reaper fired within 60 seconds and tore down sessions that survived a rolling deploy with their VMs still running and the learner still connected. This defeated the purpose of the graceful restart path entirely.

**Session 29 correction (commit c0ae237):** Removed the `expires_at` override. Sessions are now only marked `suspect=True` (a UI hint) without touching their expiry. Instead, environments stuck in `"provisioning"` state at startup are immediately faulted, ensuring the reconciler's auto-recovery path handles them. Environments whose sessions survive (status `"busy"`) are left untouched — their sessions remain valid for their original duration.

- `suspect=True`: UI can warn the learner their session survived a pod restart; session is otherwise healthy.
- Stuck-provisioning environments: faulted immediately so the reconciler auto-recovers them.
- Reaper continues to handle natural session expiry; no forced-expiry bypass needed.
- Test coverage: `test_suspect_sessions_marked_on_startup` still passes (checks `suspect=True`; forced expiry assertion removed).
