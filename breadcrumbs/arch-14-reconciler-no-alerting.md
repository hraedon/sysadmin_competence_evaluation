# ~~ARCH-14~~: Reconciler Silent Failure / Health Tracking — **Closed**

## Status
- **Priority**: Medium
- **Resolved**: 2026-03-28

## Context
Background jobs like `reconcile_environments` and `reap_expired_sessions` run on a schedule. If these jobs crash (e.g., due to database locks or unexpected API errors), there was no external visibility into their failure. They would fail silently in the background, only visible in container logs.

## Resolution
1. **Heartbeat Table**: Added `LabHeartbeat` model to `app/database.py` to track the last run time, status, and error message for named jobs.
2. **Job Wrappers**: Refactored `reap_expired_sessions_wrapper` and `reconcile_environments_wrapper` in `app/services/lab_service.py` to:
   - Catch all exceptions.
   - Log failures to the `heartbeats` table.
   - Record successful runs.
3. **Health Endpoint**: Added `/health` to `app/main.py` which returns the current status of all background heartbeats.

## Verification
- Added `test_reaper_logs_heartbeat` and `test_reconciler_logs_heartbeat` to `test_integration.py`.
- Verified that these tests correctly record "success" in the database after a successful run.
