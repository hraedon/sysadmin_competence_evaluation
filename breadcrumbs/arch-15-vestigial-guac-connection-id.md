# ARCH-15: Vestigial guac_connection_id on LabEnvironment

## Severity
Low (technical debt)

## Location
- `platform/lab-controller/app/database.py` — `LabEnvironment.guac_connection_id`
- `platform/lab-controller/environments.yaml` — `guac_connection_id` field on each environment
- `platform/lab-controller/app/main.py` — `load_environments()` reads and stores the field

## Description
`LabEnvironment.guac_connection_id` was used for static pre-configured Guacamole connections
before SEC-02 introduced ephemeral per-session connections. Since Session 28, the provisioning
flow creates a dynamic connection and stores its ID on `LabSession.guac_connection_id` instead.
The static ID on `LabEnvironment` is never read during provisioning, teardown, or reconciliation.

The field exists in:
- The SQLAlchemy model (parsed and stored on startup)
- `environments.yaml` (currently `"1"` for both `env-windows-01` and `env-domain-01` — same ID,
  which would have been a bug if the static ID were still used)
- The `load_environments()` upsert logic

Keeping it creates minor confusion: readers might assume the static ID is used for connections
and spend time tracing a code path that is a dead end.

## Remediation

1. Remove `guac_connection_id` from `LabEnvironment` model, `load_environments()`, and
   `environments.yaml`.
2. Add a migration step to `_migrate_add_columns()` that drops the column (SQLite requires
   a table-rename approach: create new table without column, copy data, rename; or simply
   leave the orphaned column since SQLite tolerates extra columns harmlessly).
3. Do this after confirming that no existing code path reads `LabEnvironment.guac_connection_id`
   (a grep confirms: only `load_environments()` writes it; nothing reads it for connections).

## Note
`LabSession.guac_connection_id` is NOT vestigial — it stores the dynamic connection ID created
during provisioning and is read by teardown and the session polling endpoint. Only the
`LabEnvironment` column is the dead one.

## Related
SEC-02 (ephemeral connections, now closed)
