# SEC-04: Lab Controller API Has No Authentication

## Status
**RESOLVED** — Session 25 (2026-03-27)

## Severity
~~High~~ Closed

## Location
`platform/lab-controller/app/main.py` — all endpoints, particularly `POST /lab/provision/{scenario_id}` and `GET /lab/status`

## Description
Every lab controller endpoint accepts requests with no authentication. `POST /lab/provision/{scenario_id}` takes a `user_id` from the request body with no validation — any caller can provision a lab session under any arbitrary user identity. `GET /lab/status` returns the full environment inventory (names, statuses, VM targets) to any unauthenticated caller. The ingress exposes this on the public internet.

Combined with SEC-01 (credentials in process args), an unauthenticated caller can trigger WinRM execution against lab VMs.

## Remediation

Add authentication before Phase 2 goes live with real users. Minimum viable approach: a shared secret bearer token in the `Authorization` header, validated by a FastAPI dependency injected on all routes. The frontend already generates a `localStorage`-based `user_id` — that can serve as a client identifier once the API is gated behind a real auth check.

For multi-user deployments, integrate with the platform's existing user identity model (or a simple JWT scheme) so `user_id` values are issued by the platform rather than self-reported by callers.

## Related
SEC-01, SEC-02, INFRA-01

## Resolution

All sensitive endpoints in `main.py` now include `dependencies=[Depends(verify_api_key)]`. The `verify_api_key` FastAPI dependency reads `X-API-Key` from the request header and compares it to `settings.controller_api_key` (loaded from the `.env` file / k8s Secret). A mismatch returns HTTP 403.

The `/health` endpoint remains unauthenticated by design (k8s liveness probe).

The frontend-side companion issue (SEC-06, hardcoded key in LabPanel.jsx) was addressed separately — key moved to `VITE_CONTROLLER_KEY` build-time env var.
