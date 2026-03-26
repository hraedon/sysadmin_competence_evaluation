import asyncio
import logging
import json
import os
from typing import List, Optional
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestrationResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None

class HyperVOrchestrator:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    async def _run_ps(self, command: str) -> OrchestrationResult:
        """Executes a PowerShell command asynchronously and returns the result."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Executing PS: {command}")
            await asyncio.sleep(0.5) # Simulate slight overhead
            return OrchestrationResult(success=True, output="Dry run success")

        try:
            # Use -NoProfile and -NonInteractive for automation
            process = await asyncio.create_subprocess_exec(
                "powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return OrchestrationResult(success=True, output=stdout.decode().strip())
            else:
                return OrchestrationResult(
                    success=False, 
                    output=stdout.decode().strip(), 
                    error=stderr.decode().strip()
                )
        except Exception as e:
            return OrchestrationResult(success=False, output="", error=str(e))

    async def revert_to_checkpoint(self, vm_name: str, checkpoint_name: str) -> OrchestrationResult:
        """Reverts a VM to a specific snapshot/checkpoint."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Reverting {vm_name} to {checkpoint_name}...")
            await asyncio.sleep(2)
        cmd = f"Restore-VMSnapshot -VMName '{vm_name}' -Name '{checkpoint_name}' -Confirm:$false"
        return await self._run_ps(cmd)

    async def start_vm(self, vm_name: str) -> OrchestrationResult:
        """Starts a Hyper-V virtual machine."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Starting {vm_name}...")
            await asyncio.sleep(1)
        cmd = f"Start-VM -Name '{vm_name}'"
        return await self._run_ps(cmd)

    async def stop_vm(self, vm_name: str, force: bool = False) -> OrchestrationResult:
        """Stops a Hyper-V virtual machine."""
        suffix = " -TurnOff" if force else ""
        cmd = f"Stop-VM -Name '{vm_name}'{suffix}"
        return await self._run_ps(cmd)

    async def run_script_in_guest(self, vm_name: str, script_path: str) -> OrchestrationResult:
        """Runs a script inside the guest VM using PowerShell Direct (HKS)."""
        try:
            if not os.path.exists(script_path):
                return OrchestrationResult(success=False, output="", error=f"Script not found: {script_path}")
                
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            # Escape single quotes for PowerShell
            escaped_content = script_content.replace("'", "''")
            
            # Using -VMName uses PowerShell Direct (no network required, just guest services)
            # cmd = f"Invoke-Command -VMName '{vm_name}' -ScriptBlock {{ {escaped_content} }}"
            
            # For reliability, we might want to pass the script as a block:
            cmd = f"Invoke-Command -VMName '{vm_name}' -ScriptBlock {{ {escaped_content} }}"
            
            return await self._run_ps(cmd)
        except Exception as e:
            return OrchestrationResult(success=False, output="", error=f"Failed to execute script: {str(e)}")

    async def copy_file_to_guest(self, vm_name: str, source: str, destination: str) -> OrchestrationResult:
        """Copies a file from the host to the guest VM."""
        cmd = f"Copy-Item -Path '{source}' -Destination '{destination}' -VMName '{vm_name}'"
        return await self._run_ps(cmd)

    async def get_vm_ip(self, vm_name: str) -> OrchestrationResult:
        """Retrieves the primary IPv4 address of a VM from Hyper-V Guest Services."""
        cmd = f"(Get-VMNetworkAdapter -VMName '{vm_name}').IPAddresses | Where-Object {{ $_ -like '*.*' }} | Select-Object -First 1"
        return await self._run_ps(cmd)

    async def wait_for_guest_readiness(self, vm_name: str, timeout_seconds: int = 60) -> bool:
        """Polls the VM's heartbeat and network status until it's ready."""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            res = await self.get_vm_ip(vm_name)
            if res.success and res.output:
                logger.info(f"VM {vm_name} is ready with IP: {res.output}")
                return True
            await asyncio.sleep(2)
        
        logger.warning(f"Timed out waiting for VM {vm_name} to report an IP address.")
        return False
