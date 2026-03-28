# ~~ARCH-12~~: Guacamole Token Refresh — **Closed**

## Status
- **Priority**: Medium
- **Resolved**: 2026-03-28

## Context
Guacamole authentication tokens eventually expire. If the Lab Controller (a long-running service) holds a stale token, all subsequent API calls (provisioning/teardown) will fail with 401 Unauthorized.

## Resolution
The `GuacamoleClient` in `app/guacamole.py` was refactored to include a `_request` helper that:
1. Automatically authenticates if no token is present.
2. Catches 401 responses, re-authenticates, and retries the request once.
3. Clears the token if authentication fails.

This ensures the controller can recover from both token expiration and Guacamole service restarts.

## Verification
- Manual code review of `app/guacamole.py`.
- Verified that all integration tests in `test_integration.py` pass (though these use mocks for Guacamole, the logic is structurally correct).
