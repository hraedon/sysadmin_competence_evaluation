# ARCH-12: Guacamole Auth Token Not Refreshed After Service Restart

## Severity
Medium

## Location
`platform/lab-controller/app/guacamole.py` — `GuacamoleClient._authenticate()`, `create_connection()`, `delete_connection()`

## Description
`GuacamoleClient` is a module-level singleton that caches its auth token in `self.token` after the
first successful call to `_authenticate()`. Both `create_connection()` and `delete_connection()`
check `if not self.token` before authenticating — meaning they only re-authenticate when the token
is `None`.

If Guacamole restarts (or the token expires server-side), `self.token` still holds the old value.
The next API call will fail with HTTP 401, but neither method handles 401 — they log an error and
raise a generic exception. The token is never cleared, so every subsequent call also fails.

Failure modes:
- **Session creation silently proceeds without a Guacamole URL.** `run_provisioning_flow()` catches
  the `create_connection` exception at line ~481, but if `guac_target_vm` is set and the IP resolves,
  the exception propagates and marks the environment `faulted`. The learner never gets a console URL.
- **Teardown leaks connections.** `delete_connection` in `teardown_environment_logic()` catches and
  logs the error but continues, so stale Guacamole connections accumulate until manually pruned.
- **Session polling returns no URL.** `get_session_status()` attempts `_authenticate()` on the
  unauthenticated path (`if not guac_client.token`) but that guard won't fire if the token is stale.

## Remediation

Add a `_ensure_token()` helper that catches HTTP 401 from API calls and retries once after
re-authentication:

```python
async def _ensure_authenticated(self):
    """Authenticate if we have no token; re-authenticate if the existing token is rejected."""
    if not self.token:
        await self._authenticate()

async def _api_call_with_reauth(self, method, url, **kwargs):
    """Execute an httpx call, retrying once with fresh auth if 401 is returned."""
    if not self.token:
        await self._authenticate()
    async with httpx.AsyncClient() as client:
        response = await getattr(client, method)(url, **kwargs)
        if response.status_code == 401:
            self.token = None
            await self._authenticate()
            # Rebuild URL with new token and retry
            response = await getattr(client, method)(url.replace(
                f"token={kwargs.get('_old_token', '')}", f"token={self.token}"
            ), **kwargs)
        return response
```

A simpler alternative: clear `self.token = None` before any API call that returns a non-2xx
status, so the next call will re-authenticate.

## Related
SEC-02 (ephemeral Guacamole connections), session polling endpoint
