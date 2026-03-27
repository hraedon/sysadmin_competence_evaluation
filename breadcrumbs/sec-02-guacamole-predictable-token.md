# SEC-02: Guacamole Client Token Is Trivially Predictable

## Severity
High

## Location
`platform/lab-controller/app/main.py` — `guac_client_token()` (line ~88) and `/lab/provision/{scenario_id}` response (line ~322)

## Description
The Guacamole client URL handed back to the user is constructed as:

```python
base64(connection_id + "\x00c\x00postgresql")
```

`connection_id` is a static value from `environments.yaml` — it never rotates per session. Any user who completes one session can decode the token, enumerate the other connection IDs (which are also in the public repo, see INFRA-01), and construct a valid Guacamole URL for any other environment without going through the lab controller at all. There is no per-session credential or expiry protecting the RDP/SSH access.

`create_connection()` already exists in `guacamole.py` but is never called during provisioning. The Guacamole REST API supports creating ephemeral per-session connections with time-limited tokens — this is the correct pattern.

## Remediation

Replace the static `guac_client_token()` approach with a call to `create_connection()` during provisioning that creates an ephemeral Guacamole connection tied to the session. Return the resulting per-session token rather than a token derived from the static connection ID. Connections should be deleted (or expire automatically) when the session ends.

## Related
INFRA-01 (environments.yaml in public repo), SEC-04 (no API auth)
