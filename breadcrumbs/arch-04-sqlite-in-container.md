# ARCH-04: SQLite Hardcoded in Containerized Lab Controller — **Resolved**

## Severity
~~Medium~~ **Closed**

## Location
`platform/lab-controller/app/database.py` — line 9: `SQLALCHEMY_DATABASE_URL = "sqlite:///./lab_state.db"`

## Description
The lab controller's database is hardcoded to a SQLite file at `./lab_state.db` relative to the container's working directory. This means:

1. **Pod restart wipes all state.** Environment pool status and active sessions are lost on every redeployment, controller crash, or k8s rescheduling. The startup flush logic (ARCH-02) partially masks this, but the root cause is a non-persistent database.
2. **Horizontal scaling is impossible.** Two pod replicas would have two separate SQLite databases — the environment pool would be split, the atomic mutex (ARCH-01) would be meaningless, and sessions would be invisible across replicas.
3. **No durability guarantees.** SQLite on a container-local filesystem has no replication, no WAL durability across container boundaries, and is lost on node eviction.

`mvmpostgres01.ad.hraedon.com` is already available and reachable from the cluster per the build notes.

## Resolution

`database.py` now reads `SQLALCHEMY_DATABASE_URL` from the environment (`os.getenv`), falling back to SQLite for local development. The k8s deployment wires it to a `lab-controller-secret` key (`DATABASE_URL`). SQLAlchemy engine creation branches on SQLite vs PostgreSQL (connection pooling, `check_same_thread` for SQLite). Alembic migrations run automatically on PostgreSQL startup. Resolved prior to Session 32.

## Related
ARCH-01 (race condition fix requires Postgres — now possible), ARCH-02 (session flush partially caused by non-persistent DB — root cause eliminated)
