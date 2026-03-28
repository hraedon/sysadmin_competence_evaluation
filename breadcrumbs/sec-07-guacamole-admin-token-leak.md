# SEC-07: Global Guacamole Admin Token Leaked to Browser Client

## Severity
High

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

## Related
SEC-02 (Guacamole predictable token — previously closed, but this "admin token leak" is a more fundamental credential exposure).
