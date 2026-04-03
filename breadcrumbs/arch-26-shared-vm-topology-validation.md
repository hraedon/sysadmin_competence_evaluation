# ~~ARCH-26~~: Shared-VM Topology Validation — **Closed**

## Status
- **Priority**: Medium
- **Resolved**: 2026-04-02

## Context
`env-windows-01` and `env-domain-01` both claim `["LabDC01", "LabServer01"]` in `environments.yaml`. These environments are mutually exclusive — they cannot run concurrently because they share physical VMs. This topology caused ARCH-23 (reconciler false positive: it reverted running VMs against the "available" environment entry while a session was active on the other entry).

ARCH-23 was fixed in Session 29 by building a set of active VMs and skipping them during orphan detection. However, nothing prevented someone from creating *new* overlapping environment entries in `environments.yaml`, which would reintroduce the same class of bugs.

## Resolution
Added startup validation in `load_environments()`. After loading all environments, the function builds a map of VM-to-environment-IDs. If any VM appears in multiple environments, a warning is logged naming the specific overlap. This doesn't prevent operation (the overlap may be intentional, as it is here), but makes the constraint visible rather than implicit.

## Related
ARCH-23 (reconciler shared-VM orphan false positive — the bug this validation prevents from recurring)
