"""
Abstract base class for VM orchestration backends.

Each hypervisor platform (Hyper-V, Proxmox, etc.) implements this interface.
The lab service layer calls these methods without knowing which backend is active.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class OrchestrationResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None


class Orchestrator(ABC):
    """
    Abstract interface for VM lifecycle management.

    Implementations must support:
    - Snapshot/checkpoint revert and VM start/stop
    - Guest OS readiness detection
    - Script execution and file transfer inside guest VMs
    - VM power state queries (for reconciler)
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    @abstractmethod
    async def revert_to_checkpoint(self, vm_name: str, checkpoint_name: str) -> OrchestrationResult:
        """Revert a VM to a named snapshot/checkpoint."""
        ...

    @abstractmethod
    async def start_vm(self, vm_name: str) -> OrchestrationResult:
        """Start a VM."""
        ...

    @abstractmethod
    async def stop_vm(self, vm_name: str, force: bool = False) -> OrchestrationResult:
        """Stop a VM. If force=True, perform a hard power-off."""
        ...

    @abstractmethod
    async def get_vm_ip(self, vm_name: str) -> OrchestrationResult:
        """Get the primary IPv4 address of a running VM."""
        ...

    @abstractmethod
    async def test_guest_connectivity(self, vm_name: str) -> OrchestrationResult:
        """Confirm the guest OS is responsive (not just that the VM is running)."""
        ...

    @abstractmethod
    async def get_vm_state(self, vm_name: str) -> OrchestrationResult:
        """Get the current power state of a VM (e.g. 'Running', 'Off', 'stopped', 'running')."""
        ...

    @abstractmethod
    async def run_script_in_guest(self, vm_name: str, script_path: str) -> OrchestrationResult:
        """Execute a local script file inside the guest VM and return its output."""
        ...

    @abstractmethod
    async def copy_file_to_guest(self, vm_name: str, source: str, destination: str) -> OrchestrationResult:
        """Copy a file from the orchestrator's filesystem into the guest VM."""
        ...

    async def wait_for_guest_readiness(
        self,
        vm_name: str,
        timeout_seconds: int = 300,
        on_connectivity_phase: Optional[Callable[[], Awaitable[None]]] = None,
    ) -> bool:
        """Poll the VM for an IP address, then confirm with a connectivity test.

        This default implementation works for any backend that implements
        get_vm_ip() and test_guest_connectivity(). Override if your backend
        has a more efficient readiness detection mechanism.
        """
        start_time = asyncio.get_running_loop().time()

        # Phase 1: wait for IP address
        while asyncio.get_running_loop().time() - start_time < timeout_seconds:
            res = await self.get_vm_ip(vm_name)
            if res.success and res.output:
                logger.info(f"VM {vm_name} has IP: {res.output}")
                break
            await asyncio.sleep(2)
        else:
            logger.warning(f"Timeout waiting for {vm_name} IP address.")
            return False

        # Phase 2: confirm guest OS is responsive
        if on_connectivity_phase:
            await on_connectivity_phase()
        remaining = timeout_seconds - (asyncio.get_running_loop().time() - start_time)
        conn_start = asyncio.get_running_loop().time()
        while asyncio.get_running_loop().time() - conn_start < remaining:
            conn_res = await self.test_guest_connectivity(vm_name)
            if conn_res.success:
                logger.info(f"VM {vm_name} guest OS confirmed responsive.")
                return True
            await asyncio.sleep(3)
        logger.warning(f"Timeout waiting for {vm_name} guest connectivity.")
        return False
