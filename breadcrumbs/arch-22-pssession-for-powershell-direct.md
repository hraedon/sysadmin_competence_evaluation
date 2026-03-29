# ARCH-22: PSSession for PowerShell Direct and Hardened Provisioning

## Status
- **Priority**: High (Stability)
- **Resolved**: 2026-03-28

## Context
Provisioning was consistently failing with `NotImplemented: The FileSystem provider supports credentials only on the New-PSDrive cmdlet`. This was caused by `Copy-Item -VMName` being called with a `-Credential` parameter, which is not supported for PowerShell Direct in the same way as `Invoke-Command`.

Additionally, if provisioning timed out or failed partially, VMs could be left in a "Running" state without an active session, requiring manual intervention or waiting for the reconciler.

## Resolution
1. **Refactored Orchestrator**: Updated `app/orchestrator.py` to use `New-PSSession -VMName` for PowerShell Direct operations. This creates a persistent session that correctly handles credentials for both `Copy-Item -ToSession` and `Invoke-Command -Session`.
2. **Hardened Provisioning Flow**: Updated `app/services/lab_service.py` to explicitly call `teardown_environment_logic` if a provisioning watchdog timeout occurs or if an internal exception is raised. This ensures that any VMs started during a failed attempt are immediately reverted and stopped.
3. **Smoke Testing**: Added `tests/test_smoke.py` which provides a way to verify real WinRM and PowerShell Direct connectivity against the actual Hyper-V infrastructure (requires real credentials in `.env`).

## Verification
- Verified via `tests/smoke_test.py` (and subsequently `test_smoke.py`) that the `New-PSSession` logic correctly establishes guest connectivity and allows file operations on `LabServer01`.
- All integration tests passing.
- Reset all faulted environments via the admin API.
