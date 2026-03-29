# ARCH-20: Frontend JWT Token Refresh Not Wired

## Severity
Low/Medium

## Location
`platform/frontend/src/lib/auth.js`
`platform/lab-controller/app/routers/auth.py`

## Description
The backend issues access tokens that expire after 60 minutes (`access_token_expire_minutes=60` in settings). A refresh token endpoint exists (`POST /auth/refresh`) and the backend issues both tokens at login. However, the frontend has no logic to use the refresh token before the access token expires.

**Failure mode:** After 60 minutes of session time, all authenticated API calls (`/api/evaluate`, `/lab/provision`, etc.) silently return HTTP 401. The user gets no indication that their session has lapsed — requests simply fail, appearing as network errors or evaluation failures.

## Remediation
In `auth.js`, add a proactive token refresh: before any authenticated fetch, check if the access token is within ~5 minutes of expiry (decode the JWT `exp` claim client-side without verifying the signature — just to read the timestamp), and call `POST /auth/refresh` if so. Store the refreshed token in localStorage. Alternatively, add a global 401 interceptor that attempts a refresh and retries the original request once before prompting re-login.

## Related
ARCH-09
