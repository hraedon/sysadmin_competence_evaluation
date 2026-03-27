# ARCH-06: No Rate Limiting on Lab Controller or Evaluate Path

## Severity
Low (pending SEC-04 fix), Medium (if API remains unauthenticated)

## Location
`platform/lab-controller/app/main.py` — all endpoints
`platform/frontend/src/App.jsx` — evaluate submit button

## Description
No rate limiting exists on any endpoint. Two distinct surfaces:

**Lab controller** (`POST /lab/provision/{scenario_id}`): Each call attempts to provision a real Hyper-V environment. Without rate limiting, a caller can exhaust the entire environment pool in seconds by flooding the endpoint. Combined with SEC-04 (no authentication), this requires no credentials at all. The environments lock in "provisioning" state and are unavailable until they either time out (ARCH-03, which currently has no outer timeout) or are manually reset.

**Frontend evaluate path**: The submit button has no debounce or cooldown. A user can submit dozens of API calls per minute against their own key or the backend proxy. This is a minor concern for self-hosted single-user deployments but becomes relevant for any shared or hosted instance.

## Remediation

**Lab controller**: Add `slowapi` rate limiting (the standard FastAPI rate limiting library) to `/lab/provision`. A per-IP limit of 5 requests/minute is sufficient to prevent pool exhaustion while allowing legitimate retries. Note: fixing SEC-04 (adding authentication) reduces the blast radius significantly — an authenticated user exhausting their own session quota is a different risk than an unauthenticated caller exhausting shared infrastructure.

**Frontend**: Add a brief cooldown (3–5 seconds) on the evaluate button after submission, implemented as a `submitting` state already partially in place. This prevents accidental double-submits and limits runaway cost on proxy deployments.

Address after SEC-04 — authentication is the higher-priority control that changes what rate limiting needs to protect.

## Related
SEC-04 (authentication eliminates anonymous pool exhaustion risk), ARCH-03 (stuck provisioning flows amplify pool exhaustion impact)
