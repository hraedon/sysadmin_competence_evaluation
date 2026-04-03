"""
Proxmox VE orchestrator — manages VMs via the Proxmox REST API.

Uses the Proxmox API for VM lifecycle (snapshots, start/stop, state queries)
and the QEMU Guest Agent for in-guest operations (script execution, file transfer).

Requires:
- proxmoxer library (pip install proxmoxer requests)
- QEMU Guest Agent installed and running in guest VMs
- Proxmox API token with appropriate permissions
"""

import asyncio
import base64
import json
import logging
import os
from typing import Optional

from .orchestrator_base import Orchestrator, OrchestrationResult

logger = logging.getLogger(__name__)


class ProxmoxOrchestrator(Orchestrator):
    """
    Manages VMs on a Proxmox VE cluster via its REST API.

    Key differences from Hyper-V:
    - Snapshots (not checkpoints): `POST /nodes/{node}/qemu/{vmid}/snapshot/{snap}/rollback`
    - VM start/stop: `POST /nodes/{node}/qemu/{vmid}/status/start|stop`
    - Guest agent for in-VM ops: `POST /nodes/{node}/qemu/{vmid}/agent/exec`
    - File transfer via guest agent: `file-write` / `file-read` agent commands
    - IP addresses via guest agent: `GET /nodes/{node}/qemu/{vmid}/agent/network-get-interfaces`

    VM identification: Proxmox uses numeric VMIDs. The `vm_name` parameter in
    the Orchestrator interface maps to VMID via a lookup table populated from
    environments.yaml (e.g., "LabServer01" -> "100").
    """

    def __init__(
        self,
        api_url: str,
        api_token_id: str,
        api_token_secret: str,
        node: str = "pve",
        verify_ssl: bool = False,
        vm_name_to_id: Optional[dict] = None,
        dry_run: bool = True,
    ):
        super().__init__(dry_run=dry_run)
        self.api_url = api_url.rstrip("/")
        self.api_token_id = api_token_id
        self.api_token_secret = api_token_secret
        self.node = node
        self.verify_ssl = verify_ssl
        self.vm_name_to_id = vm_name_to_id or {}
        self._session = None  # Lazy-initialized aiohttp session

    def _resolve_vmid(self, vm_name: str) -> str:
        """Resolve a friendly VM name to a Proxmox VMID."""
        if vm_name in self.vm_name_to_id:
            return str(self.vm_name_to_id[vm_name])
        # If the name is already a numeric ID, use it directly
        if vm_name.isdigit():
            return vm_name
        raise ValueError(f"Cannot resolve VM name '{vm_name}' to a Proxmox VMID. "
                         f"Known mappings: {self.vm_name_to_id}")

    def _auth_headers(self) -> dict:
        """Return Proxmox API authentication headers."""
        return {"Authorization": f"PVEAPIToken={self.api_token_id}={self.api_token_secret}"}

    async def _api_request(self, method: str, path: str, data: dict = None) -> OrchestrationResult:
        """Make an authenticated request to the Proxmox API.

        TODO: Implement with aiohttp when proxmoxer async support is needed.
        For now, this is a stub that documents the intended API surface.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox API {method} {path}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="Dry run success")

        # TODO: Implement actual HTTP calls
        # url = f"{self.api_url}{path}"
        # async with aiohttp.ClientSession() as session:
        #     async with session.request(method, url, headers=self._auth_headers(),
        #                                json=data, ssl=self.verify_ssl) as resp:
        #         body = await resp.json()
        #         if resp.status < 300:
        #             return OrchestrationResult(success=True, output=json.dumps(body.get("data", {})))
        #         else:
        #             return OrchestrationResult(success=False, output="", error=f"HTTP {resp.status}: {body}")

        return OrchestrationResult(success=False, output="", error="ProxmoxOrchestrator not yet implemented")

    async def _wait_for_task(self, upid: str, timeout: int = 120) -> bool:
        """Wait for a Proxmox task (identified by UPID) to complete.

        TODO: Poll GET /nodes/{node}/tasks/{upid}/status until status is 'stopped'.
        """
        if self.dry_run:
            return True
        # TODO: Implement task polling
        return False

    # -----------------------------------------------------------------------
    # Orchestrator interface implementation
    # -----------------------------------------------------------------------

    async def revert_to_checkpoint(self, vm_name: str, checkpoint_name: str) -> OrchestrationResult:
        """Rollback VM to a named snapshot."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: reverting {vm_name} to snapshot '{checkpoint_name}'")
            await asyncio.sleep(2)
            return OrchestrationResult(success=True, output="Dry run success")

        vmid = self._resolve_vmid(vm_name)
        return await self._api_request(
            "POST",
            f"/api2/json/nodes/{self.node}/qemu/{vmid}/snapshot/{checkpoint_name}/rollback"
        )

    async def start_vm(self, vm_name: str) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: starting {vm_name}")
            await asyncio.sleep(1)
            return OrchestrationResult(success=True, output="Dry run success")

        vmid = self._resolve_vmid(vm_name)
        return await self._api_request("POST", f"/api2/json/nodes/{self.node}/qemu/{vmid}/status/start")

    async def stop_vm(self, vm_name: str, force: bool = False) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: stopping {vm_name} (force={force})")
            await asyncio.sleep(1)
            return OrchestrationResult(success=True, output="Dry run success")

        vmid = self._resolve_vmid(vm_name)
        action = "stop" if force else "shutdown"
        return await self._api_request("POST", f"/api2/json/nodes/{self.node}/qemu/{vmid}/status/{action}")

    async def get_vm_ip(self, vm_name: str) -> OrchestrationResult:
        """Get VM IP via QEMU Guest Agent network-get-interfaces."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: getting IP for {vm_name}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="192.168.100.15")

        vmid = self._resolve_vmid(vm_name)
        res = await self._api_request("GET", f"/api2/json/nodes/{self.node}/qemu/{vmid}/agent/network-get-interfaces")
        if not res.success:
            return res

        # TODO: Parse the interface list to extract the first non-loopback IPv4 address
        # interfaces = json.loads(res.output)
        # for iface in interfaces:
        #     for addr in iface.get("ip-addresses", []):
        #         if addr["ip-address-type"] == "ipv4" and not addr["ip-address"].startswith("127."):
        #             return OrchestrationResult(success=True, output=addr["ip-address"])
        return OrchestrationResult(success=False, output="", error="IP parsing not yet implemented")

    async def test_guest_connectivity(self, vm_name: str) -> OrchestrationResult:
        """Test guest responsiveness via QEMU Guest Agent ping."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: testing connectivity for {vm_name}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="OK")

        vmid = self._resolve_vmid(vm_name)
        return await self._api_request("GET", f"/api2/json/nodes/{self.node}/qemu/{vmid}/agent/ping")

    async def get_vm_state(self, vm_name: str) -> OrchestrationResult:
        """Get VM power state from Proxmox."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: getting state for {vm_name}")
            return OrchestrationResult(success=True, output="stopped")

        vmid = self._resolve_vmid(vm_name)
        res = await self._api_request("GET", f"/api2/json/nodes/{self.node}/qemu/{vmid}/status/current")
        if not res.success:
            return res

        # TODO: Parse status — Proxmox returns "running", "stopped", etc.
        # data = json.loads(res.output)
        # return OrchestrationResult(success=True, output=data.get("status", "unknown"))
        return OrchestrationResult(success=False, output="", error="State parsing not yet implemented")

    async def run_script_in_guest(self, vm_name: str, script_path: str) -> OrchestrationResult:
        """Execute a script inside the guest VM via QEMU Guest Agent.

        The script is read from the local filesystem, transferred to the guest
        via the guest agent's file-write command, then executed via guest-exec.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: running script in {vm_name}: {script_path}")
            await asyncio.sleep(1)
            return OrchestrationResult(
                success=True,
                output='{"status":"correct","detail":"Dry run verification passed."}'
            )

        if not os.path.exists(script_path):
            return OrchestrationResult(success=False, output="", error=f"Script not found: {script_path}")

        # TODO: Implement guest agent file-write + exec
        # 1. Read script content
        # 2. POST /nodes/{node}/qemu/{vmid}/agent/file-write with content
        # 3. POST /nodes/{node}/qemu/{vmid}/agent/exec with the script path
        # 4. GET /nodes/{node}/qemu/{vmid}/agent/exec-status?pid={pid} to get output
        return OrchestrationResult(success=False, output="", error="Guest script execution not yet implemented")

    async def copy_file_to_guest(self, vm_name: str, source: str, destination: str) -> OrchestrationResult:
        """Copy a file into the guest VM via QEMU Guest Agent file-write."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: copying {source} -> {vm_name}:{destination}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="Dry run success")

        if not os.path.exists(source):
            return OrchestrationResult(success=False, output="", error=f"Source not found: {source}")

        # TODO: Implement guest agent file-write
        # with open(source, 'rb') as f:
        #     content = base64.b64encode(f.read()).decode('ascii')
        # POST /nodes/{node}/qemu/{vmid}/agent/file-write
        #   {"file": destination, "content": content, "encode": True}
        return OrchestrationResult(success=False, output="", error="Guest file copy not yet implemented")
