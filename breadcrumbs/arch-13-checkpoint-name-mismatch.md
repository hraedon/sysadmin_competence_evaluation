# ARCH-13: Baseline Checkpoint Name Inconsistency — Operational Footgun

## Severity
High (before enabling non-dry-run) / Low (in dry-run)

## Location
- `platform/lab-controller/app/main.py` — `Settings.baseline_checkpoint_name` (default `"Baseline"`)
- `scenarios/d01/lab_fix_the_log_writer/scenario.yaml` — `presentation.modes.E.checkpoint: "Baseline Checkpoint"`
- `platform/lab-controller/environments.yaml` — (no checkpoint field; teardown/reconciler use the setting)

## Description
There are two separate checkpoint name references in the codebase that must agree with the
actual Hyper-V snapshot name, but can diverge:

1. **Provisioning** reads from the scenario YAML via `mode_e.get('checkpoint', 'Baseline')`.
   The `d01-lab-fix-the-log-writer` scenario specifies `"Baseline Checkpoint"` (with a space).

2. **Teardown and reconciler** use `settings.baseline_checkpoint_name`, which defaults to
   `"Baseline"` (no space).

If the Hyper-V VM snapshots are named `"Baseline Checkpoint"` (matching the scenario YAML),
then:
- Provisioning works — correct checkpoint name from YAML.
- Teardown fails — `"Baseline"` checkpoint not found → `Restore-VMSnapshot` returns an error →
  environment marked `faulted` → reconciler picks it up → reconciler also fails → fault_retry_count
  increments → after 2 retries, environment permanently faulted and every session leaks a running VM.

This was previously hidden because teardown hardcoded `"Baseline"` and was never exercised
against real VMs. The reconciler now surfaces the same path.

## Remediation

**Immediate (operator action required before enabling DRY_RUN=False):**

1. Check what the snapshots are actually named on the Hyper-V VMs:
   ```powershell
   Get-VMSnapshot -VMName LabServer01 | Select Name
   Get-VMSnapshot -VMName LabDC01 | Select Name
   Get-VMSnapshot -VMName LabLinux01 | Select Name
   ```

2. Set `BASELINE_CHECKPOINT_NAME` in `.env` / k8s Secret to match exactly.

3. Update scenario YAMLs (or add a default) so provisioning also uses the setting rather
   than a hardcoded YAML value. Alternatively, add a validation step at startup that reads
   each scenario's `checkpoint` field and warns if it doesn't match `baseline_checkpoint_name`.

**Longer term:**
Move `checkpoint` out of scenario YAML and into `environments.yaml` (per-environment snapshot name),
since the checkpoint name is a property of the Hyper-V environment, not the scenario.

## Related
ARCH-03 (provisioning watchdog), reconciler (`reconcile_environments()`), `teardown_environment_logic()`
