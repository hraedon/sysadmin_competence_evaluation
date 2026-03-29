# SEC-07: Global Guacamole Admin Token Leaked to Browser Client — **Partially Resolved**

## Status
- **Original severity**: High
- **Current severity**: Low (admin token used only as fallback)
- **Partially resolved**: 2026-03-28

## Location
`platform/lab-controller/app/guacamole.py` — `_client_url()` (line ~43)
`platform/lab-controller/app/main.py` — `get_session_status()` (line ~760)

## Description
The `GuacamoleClient` in the lab controller authenticates using a service account (administrative) credential. The resulting `authToken` is then appended as a query parameter (`?token=...`) to the Guacamole URL returned to the frontend.

Because this token is an administrative token for the entire Guacamole data source, any learner who receives their lab URL can:
1.  Access the Guacamole settings/admin interface.
2.  See and join other active lab sessions.
3.  Delete connections, users, or the entire data source configuration.
4.  Exfiltrate connection parameters (hostnames, passwords) for all configured lab environments.

## Remediation
Guacamole supports a "parameter-token" system or an extension-based auth (like the `guacamole-auth-hmac` or `guacamole-auth-json` extensions) which allows the backend to generate a time-limited, connection-specific token. 

The lab controller should:
1.  Continue using the admin token for *creating* the connection via the REST API.
2.  Generate a *separate*, restricted user/token (or use a signed JSON/HMAC token) that only has access to the specific connection ID created for that session.
3.  Only return the restricted token to the browser.

## Partial Resolution (2026-03-28)
`GuacamoleClient.create_session_user()` now creates a temporary Guacamole user restricted to a single connection on provisioning. `authenticate_session_user()` returns a scoped token for that user, and `_session_client_url()` builds the URL with the restricted token. The admin token is now only sent to the browser as a fallback when session user creation fails (`lab.py:get_session_status`). The fallback path still exposes the admin token.

**Remaining risk:** The admin token fallback in `lab.py` should log a security warning and optionally refuse to return the URL rather than silently degrade. The `_client_url()` admin-token method remains as dead code until the fallback is removed.

## Related
SEC-02 (Guacamole predictable token — previously closed, but this "admin token leak" is a more fundamental credential exposure).
