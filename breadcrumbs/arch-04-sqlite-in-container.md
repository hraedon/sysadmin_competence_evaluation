# ARCH-04: SQLite Hardcoded in Containerized Lab Controller

## Severity
Medium

## Location
`platform/lab-controller/app/database.py` — line 9: `SQLALCHEMY_DATABASE_URL = "sqlite:///./lab_state.db"`

## Description
The lab controller's database is hardcoded to a SQLite file at `./lab_state.db` relative to the container's working directory. This means:

1. **Pod restart wipes all state.** Environment pool status and active sessions are lost on every redeployment, controller crash, or k8s rescheduling. The startup flush logic (ARCH-02) partially masks this, but the root cause is a non-persistent database.
2. **Horizontal scaling is impossible.** Two pod replicas would have two separate SQLite databases — the environment pool would be split, the atomic mutex (ARCH-01) would be meaningless, and sessions would be invisible across replicas.
3. **No durability guarantees.** SQLite on a container-local filesystem has no replication, no WAL durability across container boundaries, and is lost on node eviction.

`mvmpostgres01.ad.hraedon.com` is already available and reachable from the cluster per the build notes.

## Remediation

Replace the hardcoded SQLite URL with a configurable connection string read from an environment variable:

```python
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "sqlite:///./lab_state.db"  # local dev fallback only
)
```

Wire the production URL to `mvmpostgres01` via a k8s Secret. SQLAlchemy already supports Postgres; the model definitions should require no changes. The SQLite fallback keeps local development working without a Postgres instance.

This should be done before any multi-session or multi-user scenario, and is a prerequisite for ARCH-01 (SELECT FOR UPDATE requires Postgres row-level locking; SQLite advisory locks are not equivalent).

## Related
ARCH-01 (race condition fix requires Postgres), ARCH-02 (session flush partially caused by non-persistent DB)
