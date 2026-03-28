# ARCH-03: run_provisioning_flow Has No Outer Timeout

## Severity
~~Medium~~ **Closed** — resolved Session 27

## Location
`platform/lab-controller/app/main.py` — `run_provisioning_flow()` (line ~333), called via `asyncio.get_event_loop().run_in_executor()`

## Description
`wait_for_guest_readiness` has a 60-second timeout, but the overall `run_provisioning_flow` coroutine has no outer watchdog. If a provisioning script hangs indefinitely (script error, VM unresponsive after readiness check, WinRM stall during script execution), the environment stays locked in `"provisioning"` with no recovery path.

The session reaper checks `expires_at` on `LabSession` records — but a stuck environment in `"provisioning"` state may not have a session record created yet (the session is created before the background task starts, but if the task never completes, the environment status never advances past `"provisioning"`). The reaper will expire the session but the environment record status won't reset to `"available"`.

## Remediation

Wrap `run_provisioning_flow` in `asyncio.wait_for()` with a configurable provisioning timeout (e.g., 5 minutes). On timeout, set the environment status to `"faulted"` and log the failure. Add a reaper path that resets `"faulted"` environments after a configurable grace period (or on next startup, more gracefully than the current hard delete).

```python
try:
    await asyncio.wait_for(run_provisioning_flow(...), timeout=settings.provisioning_timeout_seconds)
except asyncio.TimeoutError:
    # set env status to faulted
```

## Related
ARCH-01, ARCH-02

## Resolution — Session 27

`run_provisioning_with_watchdog()` wraps the entire provisioning flow in `asyncio.wait_for()` with a configurable timeout (`settings.provisioning_timeout_seconds`, default 600s / 10 minutes). On timeout, the environment status is set to `"faulted"` with a descriptive error message via `_update_env_status()`. The background task in the provision endpoint now calls `run_provisioning_with_watchdog` instead of `run_provisioning_flow` directly.
