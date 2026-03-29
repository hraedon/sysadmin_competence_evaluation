# ARCH-23: Reconciler Falsely Reverts VMs Shared Across Environment Entries

## Severity
High (caused active sessions to be terminated within ~5 minutes)

## Location
`platform/lab-controller/app/services/lab_service.py` — `reconcile_environments()`

## Description
The reconciler's orphan-VM check iterated over all `available` environments and
checked whether any of their VMs were running. If a VM was running while its
environment was `available`, the reconciler treated it as an orphan and reverted
it to the baseline checkpoint.

This logic failed silently when two logical environments share the same physical
VMs. `env-windows-01` and `env-domain-01` both list `["LabDC01", "LabServer01"]`.
When `env-windows-01` is `busy` (VMs running, session active), `env-domain-01` is
`available`. The reconciler saw LabDC01 and LabServer01 running and `env-domain-01`
as available, concluded they were orphans, and reverted them — tearing down the
active `env-windows-01` session.

Because the reconciler runs every 5 minutes and the provisioning flow takes ~2
minutes, the session was always killed before the learner could do meaningful work.
The root cause was identified by code review rather than logs (the application
produces almost no operational logs under normal conditions).

## Remediation

Before the orphan check, build a set of all VMs currently claimed by any
environment in an active state (`busy`, `provisioning`, `teardown`). Skip any VM
that appears in this set during the per-environment orphan check.

```python
active_vms: set = set()
for e in db.query(LabEnvironment).filter(
    LabEnvironment.status.in_(["busy", "provisioning", "teardown"])
).all():
    active_vms.update(e.vms or [])

for env_id, vm_list in available_list:
    for vm in vm_list:
        if vm in active_vms:
            continue  # VM is in use by another environment — not an orphan
        ...
```

## Resolution — Session 29 (2026-03-29, commit c015102)

Implemented exactly as described above. The fix was the final link in a chain of
five bugs discovered across this session; each previous fix eliminated one failure
mode but this one was responsible for the persistent session death that survived
all earlier patches.

## Related
ARCH-01 (read-then-update without locking — same reconciler function)
