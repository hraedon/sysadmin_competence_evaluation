# ARCH-24: Proxmox VE Orchestrator Implementation

## Severity
Medium

## Location
`platform/lab-controller/app/orchestrator_proxmox.py`

## Description
The orchestrator layer has been abstracted into a base class (`orchestrator_base.py`) with `HyperVOrchestrator` as the production implementation. A `ProxmoxOrchestrator` stub exists with the correct interface but all non-dry-run operations return "not yet implemented" errors.

### What exists (2026-04-02)
- `orchestrator_base.py`: Abstract `Orchestrator` class with the full interface
- `orchestrator_proxmox.py`: Stub with dry-run support, API path documentation, and TODO markers
- `schemas.py`: `LAB_PLATFORM`, `PROXMOX_API_URL`, `PROXMOX_API_TOKEN_ID`, `PROXMOX_API_TOKEN_SECRET`, `PROXMOX_NODE` settings
- `deps.py`: Factory function that selects orchestrator based on `LAB_PLATFORM` setting
- `environments.yaml`: `platform` field on each environment entry; commented Proxmox example
- `lab_service.py`: Reconciler handles both "off" (Hyper-V) and "stopped" (Proxmox) as powered-down states

### What needs implementation
1. **HTTP client**: Use `aiohttp` for async Proxmox API calls. Add to `requirements.txt`.
2. **Task polling**: Proxmox snapshot rollback and VM start return UPIDs (async task IDs). Need `_wait_for_task()` to poll completion.
3. **Guest agent operations**: `file-write`, `exec`, `exec-status` for script execution and file transfer. Requires QEMU Guest Agent installed in VMs.
4. **IP resolution**: Parse `network-get-interfaces` response to extract primary IPv4.
5. **VM name mapping**: `vm_id_map` in environments.yaml maps friendly names to Proxmox VMIDs. Wire this into the orchestrator at startup.
6. **Console access**: Decide between Proxmox noVNC (built-in) vs Guacamole VNC. If using Guacamole, the existing `GuacamoleClient` works — just needs VNC protocol params instead of RDP.
7. **Tests**: Add `test_orchestrator_proxmox.py` with dry-run tests matching the existing integration test patterns.

### Key Proxmox API paths
- Snapshot rollback: `POST /nodes/{node}/qemu/{vmid}/snapshot/{snap}/rollback`
- VM start/stop: `POST /nodes/{node}/qemu/{vmid}/status/start|stop|shutdown`
- VM status: `GET /nodes/{node}/qemu/{vmid}/status/current`
- Guest agent: `POST /nodes/{node}/qemu/{vmid}/agent/{command}`
- Network interfaces: `GET /nodes/{node}/qemu/{vmid}/agent/network-get-interfaces`

## Related
INFRA-02 (hardcoded host FQDN — Proxmox uses API URL instead)
