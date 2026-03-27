# ARCH-01: Provisioning Race Condition — Read-Then-Update Without Row Lock

## Severity
Low (current), Medium (if replicas > 1)

## Location
`platform/lab-controller/app/main.py` — `POST /lab/provision/{scenario_id}`, lines ~272–289

## Description
The provision endpoint selects available environments and then updates one to "provisioning" in two separate ORM calls. Between the `filter(status == "available").all()` read and the `.update({"status": "provisioning"})`, a second concurrent request could select the same environment. SQLAlchemy's ORM-level `.update()` is not equivalent to `SELECT ... FOR UPDATE` — there is no row-level lock preventing concurrent reads from seeing the same available environment before either transaction commits.

**Current exposure**: `deployment.yaml` sets `replicas: 1`, so the FastAPI process is single-threaded from a request-handling perspective and the race window is narrow. This is not an active problem today.

**Future exposure**: Any scale-out to multiple replicas (or multiple k8s pods) makes this an active double-provisioning bug.

## Remediation

Use `SELECT ... FOR UPDATE SKIP LOCKED` at the database level when selecting an available environment. With SQLAlchemy this requires dropping to a `with_for_update(skip_locked=True)` query. The `SKIP LOCKED` clause ensures concurrent workers each claim a different environment atomically.

Address this before increasing replicas above 1.

## Related
ARCH-02 (session flush), ARCH-03 (provisioning timeout)
