"""
Proxmox VE orchestrator — manages VMs via the Proxmox REST API.

Uses the Proxmox API for VM lifecycle (snapshots, start/stop, state queries)
and the QEMU Guest Agent for in-guest operations (script execution, file transfer).

Requires:
- aiohttp library (pip install aiohttp)
- QEMU Guest Agent installed and running in guest VMs
- Proxmox API token with appropriate permissions
"""

import asyncio
import base64
import json
import logging
import os
import uuid
from typing import Optional
from urllib.parse import quote

import aiohttp

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
        verify_ssl: bool = True,
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
        self._session = None

    def _resolve_vmid(self, vm_name: str) -> str:
        """Resolve a friendly VM name to a Proxmox VMID."""
        if vm_name in self.vm_name_to_id:
            return str(self.vm_name_to_id[vm_name])
        if vm_name.isdigit():
            return vm_name
        raise ValueError(f"Cannot resolve VM name '{vm_name}' to a Proxmox VMID. "
                         f"Known mappings: {self.vm_name_to_id}")

    def _auth_headers(self) -> dict:
        """Return Proxmox API authentication headers."""
        return {"Authorization": f"PVEAPIToken={self.api_token_id}={self.api_token_secret}"}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazily create and reuse an aiohttp ClientSession."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=self.verify_ssl),
                timeout=aiohttp.ClientTimeout(total=30),
            )
        return self._session

    async def _api_request(self, method: str, path: str, data: Optional[dict] = None) -> OrchestrationResult:
        """Make an authenticated request to the Proxmox API.

        Unwraps the Proxmox {"data": ...} response envelope and returns the
        data as a JSON string in OrchestrationResult.output.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox API {method} {path}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="Dry run success")

        session = await self._get_session()
        url = f"{self.api_url}{path}"
        headers = self._auth_headers()

        try:
            async with session.request(method, url, headers=headers, data=data) as resp:
                try:
                    body = await resp.json()
                except Exception:
                    text = await resp.text()
                    return OrchestrationResult(
                        success=False,
                        output="",
                        error=f"HTTP {resp.status}: Non-JSON response: {text}",
                    )
                if resp.status < 300:
                    response_data = body.get("data")
                    if response_data is None and "data" in body:
                        return OrchestrationResult(
                            success=False,
                            output="",
                            error=f"HTTP {resp.status}: API returned null data",
                        )
                    if response_data is None:
                        response_data = {}
                    return OrchestrationResult(
                        success=True,
                        output=json.dumps(response_data),
                    )
                else:
                    return OrchestrationResult(
                        success=False,
                        output="",
                        error=f"HTTP {resp.status}: {body}",
                    )
        except Exception as e:
            logger.error(f"Proxmox API request failed: {method} {path}: {e}")
            return OrchestrationResult(success=False, output="", error=str(e))

    async def _wait_for_task(self, upid: str, timeout: int = 120) -> bool:
        """Wait for a Proxmox task (identified by UPID) to complete.

        Polls GET /api2/json/nodes/{node}/tasks/{upid}/status until the task
        status is 'stopped'. Returns True if the task succeeded (exitcode 0),
        False on failure or timeout. Uses exponential backoff starting at 1s,
        capped at 5s.
        """
        if self.dry_run:
            return True

        start = asyncio.get_running_loop().time()
        delay = 1.0
        while asyncio.get_running_loop().time() - start < timeout:
            res = await self._api_request(
                "GET",
                f"/api2/json/nodes/{self.node}/tasks/{quote(upid, safe='')}/status",
            )
            if not res.success:
                logger.warning(f"Task status poll failed for {upid}: {res.error}")
                return False

            if not res.output:
                logger.warning(f"Task status poll returned empty output for {upid}")
                return False
            try:
                task_data = json.loads(res.output)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse task status response for {upid}: {res.output}")
                return False
            if task_data.get("status") == "stopped":
                exitcode = task_data.get("exitcode", -1)
                if exitcode == 0:
                    return True
                logger.error(f"Task {upid} failed with exitcode {exitcode}")
                return False

            await asyncio.sleep(delay)
            delay = min(delay * 2, 5.0)

        logger.warning(f"Task {upid} timed out after {timeout}s")
        return False

    async def close(self):
        """Close the underlying aiohttp session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None
            await asyncio.sleep(0.25)

    # -----------------------------------------------------------------------
    # Orchestrator interface implementation
    # -----------------------------------------------------------------------

    async def revert_to_checkpoint(self, vm_name: str, checkpoint_name: str) -> OrchestrationResult:
        """Rollback VM to a named snapshot.

        Proxmox returns a UPID for the async rollback operation, which we poll
        to completion before returning.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: reverting {vm_name} to snapshot '{checkpoint_name}'")
            await asyncio.sleep(2)
            return OrchestrationResult(success=True, output="Dry run success")

        vmid = self._resolve_vmid(vm_name)
        res = await self._api_request(
            "POST",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/snapshot/{quote(checkpoint_name, safe='')}/rollback",
        )
        if not res.success:
            return res

        if not res.output:
            return OrchestrationResult(success=False, output="", error="Empty response from rollback API")
        try:
            upid = json.loads(res.output)
        except (json.JSONDecodeError, TypeError):
            return OrchestrationResult(success=False, output="", error=f"Failed to parse rollback response: {res.output}")
        success = await self._wait_for_task(upid)
        if success:
            return OrchestrationResult(success=True, output=res.output)
        return OrchestrationResult(
            success=False,
            output="",
            error=f"Rollback task {upid} failed or timed out",
        )

    async def start_vm(self, vm_name: str) -> OrchestrationResult:
        """Start a VM via the Proxmox API. Polls the returned UPID to completion."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: starting {vm_name}")
            await asyncio.sleep(1)
            return OrchestrationResult(success=True, output="Dry run success")

        vmid = self._resolve_vmid(vm_name)
        res = await self._api_request(
            "POST",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/status/start",
        )
        if not res.success:
            return res

        if not res.output:
            return OrchestrationResult(success=False, output="", error="Empty response from start API")
        try:
            upid = json.loads(res.output)
        except (json.JSONDecodeError, TypeError):
            return OrchestrationResult(success=False, output="", error=f"Failed to parse start response: {res.output}")
        success = await self._wait_for_task(upid)
        if success:
            return OrchestrationResult(success=True, output=res.output)
        return OrchestrationResult(
            success=False,
            output="",
            error=f"Start task {upid} failed or timed out",
        )

    async def stop_vm(self, vm_name: str, force: bool = False) -> OrchestrationResult:
        """Stop a VM via the Proxmox API. Uses 'stop' for hard power-off, 'shutdown' for graceful.

        Polls the returned UPID to completion before returning.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: stopping {vm_name} (force={force})")
            await asyncio.sleep(1)
            return OrchestrationResult(success=True, output="Dry run success")

        vmid = self._resolve_vmid(vm_name)
        action = "stop" if force else "shutdown"
        res = await self._api_request(
            "POST",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/status/{action}",
        )
        if not res.success:
            return res

        if not res.output:
            return OrchestrationResult(success=False, output="", error="Empty response from stop API")
        try:
            upid = json.loads(res.output)
        except (json.JSONDecodeError, TypeError):
            return OrchestrationResult(success=False, output="", error=f"Failed to parse stop response: {res.output}")
        success = await self._wait_for_task(upid)
        if success:
            return OrchestrationResult(success=True, output=res.output)
        return OrchestrationResult(
            success=False,
            output="",
            error=f"Stop task {upid} failed or timed out",
        )

    async def get_vm_ip(self, vm_name: str) -> OrchestrationResult:
        """Get VM IP via QEMU Guest Agent network-get-interfaces.

        Parses the interface list to extract the first non-loopback IPv4 address.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: getting IP for {vm_name}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="192.168.100.15")

        vmid = self._resolve_vmid(vm_name)
        res = await self._api_request(
            "GET",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/agent/network-get-interfaces",
        )
        if not res.success:
            return res

        if not res.output:
            return OrchestrationResult(success=False, output="", error="Empty response from network-get-interfaces")
        try:
            interfaces = json.loads(res.output)
        except (json.JSONDecodeError, TypeError):
            return OrchestrationResult(success=False, output="", error=f"Failed to parse network interface response: {res.output}")
        for iface in interfaces:
            for addr in iface.get("ip-addresses", []):
                if (
                    addr.get("ip-address-type") == "ipv4"
                    and not addr.get("ip-address", "").startswith("127.")
                ):
                    return OrchestrationResult(success=True, output=addr["ip-address"])
        return OrchestrationResult(
            success=False,
            output="",
            error="No non-loopback IPv4 address found",
        )

    async def test_guest_connectivity(self, vm_name: str) -> OrchestrationResult:
        """Test guest responsiveness via QEMU Guest Agent ping."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: testing connectivity for {vm_name}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="OK")

        vmid = self._resolve_vmid(vm_name)
        return await self._api_request(
            "GET",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/agent/ping",
        )

    async def get_vm_state(self, vm_name: str) -> OrchestrationResult:
        """Get VM power state from Proxmox.

        Returns one of: 'running', 'stopped', 'paused'.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: getting state for {vm_name}")
            return OrchestrationResult(success=True, output="stopped")

        vmid = self._resolve_vmid(vm_name)
        res = await self._api_request(
            "GET",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/status/current",
        )
        if not res.success:
            return res

        if not res.output:
            return OrchestrationResult(success=False, output="", error="Empty response from VM status API")
        try:
            data = json.loads(res.output)
        except (json.JSONDecodeError, TypeError):
            return OrchestrationResult(success=False, output="", error=f"Failed to parse VM status response: {res.output}")
        return OrchestrationResult(success=True, output=data.get("status", "unknown"))

    async def run_script_in_guest(self, vm_name: str, script_path: str) -> OrchestrationResult:
        """Execute a script inside the guest VM via QEMU Guest Agent.

        The script is read from the local filesystem, transferred to the guest
        via the guest agent's file-write command, then executed via guest-exec.
        The stdout output of the script is returned.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: running script in {vm_name}: {script_path}")
            await asyncio.sleep(1)
            return OrchestrationResult(
                success=True,
                output='{"status":"correct","detail":"Dry run verification passed."}',
            )

        if not os.path.exists(script_path):
            return OrchestrationResult(
                success=False,
                output="",
                error=f"Script not found: {script_path}",
            )

        vmid = self._resolve_vmid(vm_name)
        qvmid = quote(vmid, safe='')

        with open(script_path, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")

        remote_filename = f"{uuid.uuid4().hex}.sh"
        remote_path = f"/tmp/{remote_filename}"

        write_res = await self._api_request(
            "POST",
            f"/api2/json/nodes/{self.node}/qemu/{qvmid}/agent/file-write",
            data={"file": remote_path, "content": content, "encode": True},
        )
        if not write_res.success:
            return write_res

        try:
            exec_res = await self._api_request(
                "POST",
                f"/api2/json/nodes/{self.node}/qemu/{qvmid}/agent/exec",
                data={"command": ["/bin/bash", remote_path]},
            )
            if not exec_res.success:
                return exec_res

            if not exec_res.output:
                return OrchestrationResult(
                    success=False,
                    output="",
                    error="Empty response from guest agent exec",
                )
            try:
                exec_data = json.loads(exec_res.output)
            except (json.JSONDecodeError, TypeError):
                return OrchestrationResult(
                    success=False,
                    output="",
                    error=f"Failed to parse exec response: {exec_res.output}",
                )
            pid = exec_data.get("pid")
            if pid is None:
                return OrchestrationResult(
                    success=False,
                    output="",
                    error="No PID returned from guest agent exec",
                )

            start = asyncio.get_running_loop().time()
            delay = 1.0
            timeout = 120
            while asyncio.get_running_loop().time() - start < timeout:
                status_res = await self._api_request(
                    "GET",
                    f"/api2/json/nodes/{self.node}/qemu/{qvmid}/agent/exec-status?pid={pid}",
                )
                if not status_res.success:
                    return status_res

                if not status_res.output:
                    return OrchestrationResult(
                        success=False,
                        output="",
                        error="Empty response from exec-status",
                    )
                try:
                    status_data = json.loads(status_res.output)
                except (json.JSONDecodeError, TypeError):
                    return OrchestrationResult(
                        success=False,
                        output="",
                        error=f"Failed to parse exec-status response: {status_res.output}",
                    )
                if status_data.get("exited"):
                    exitcode = status_data.get("exitcode", -1)
                    out_data = status_data.get("out-data", "")
                    if out_data:
                        try:
                            out_data = base64.b64decode(out_data).decode("utf-8")
                        except Exception:
                            pass
                    if exitcode != 0:
                        err_data = status_data.get("err-data", "")
                        if err_data:
                            try:
                                err_data = base64.b64decode(err_data).decode("utf-8")
                            except Exception:
                                pass
                        return OrchestrationResult(
                            success=False,
                            output=out_data or "",
                            error=f"Script exited with code {exitcode}: {err_data}",
                        )
                    return OrchestrationResult(success=True, output=out_data or "")

                await asyncio.sleep(delay)
                delay = min(delay * 2, 5.0)

            return OrchestrationResult(
                success=False,
                output="",
                error=f"Guest script execution timed out after {timeout}s (pid={pid})",
            )
        finally:
            await self._api_request(
                "POST",
                f"/api2/json/nodes/{self.node}/qemu/{qvmid}/agent/exec",
                data={"command": ["/bin/rm", "-f", remote_path]},
            )

    async def copy_file_to_guest(self, vm_name: str, source: str, destination: str) -> OrchestrationResult:
        """Copy a file into the guest VM via QEMU Guest Agent file-write.

        The source file is read from the local filesystem, base64-encoded, and
        written to the destination path inside the guest via the guest agent's
        file-write command.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Proxmox: copying {source} -> {vm_name}:{destination}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="Dry run success")

        if not os.path.exists(source):
            return OrchestrationResult(
                success=False,
                output="",
                error=f"Source not found: {source}",
            )

        vmid = self._resolve_vmid(vm_name)

        with open(source, "rb") as f:
            content = base64.b64encode(f.read()).decode("ascii")

        return await self._api_request(
            "POST",
            f"/api2/json/nodes/{self.node}/qemu/{quote(vmid, safe='')}/agent/file-write",
            data={"file": destination, "content": content, "encode": True},
        )
