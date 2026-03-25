import subprocess
import logging
import json
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

    def _run_ps(self, command: str) -> OrchestrationResult:
        """Executes a PowerShell command and returns the result."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Executing PS: {command}")
            return OrchestrationResult(success=True, output="Dry run success")

        try:
            # Use -NoProfile and -NonInteractive for automation
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
                capture_output=True,
                text=True,
                check=False
            )
            
            if process.returncode == 0:
                return OrchestrationResult(success=True, output=process.stdout.strip())
            else:
                return OrchestrationResult(
                    success=False, 
                    output=process.stdout.strip(), 
                    error=process.stderr.strip()
                )
        except Exception as e:
            return OrchestrationResult(success=False, output="", error=str(e))

    def revert_to_checkpoint(self, vm_name: str, checkpoint_name: str) -> OrchestrationResult:
        """Reverts a VM to a specific snapshot/checkpoint."""
        cmd = f"Restore-VMSnapshot -VMName '{vm_name}' -Name '{checkpoint_name}' -Confirm:$false"
        return self._run_ps(cmd)

    def start_vm(self, vm_name: str) -> OrchestrationResult:
        """Starts a Hyper-V virtual machine."""
        cmd = f"Start-VM -Name '{vm_name}'"
        return self._run_ps(cmd)

    def stop_vm(self, vm_name: str, force: bool = False) -> OrchestrationResult:
        """Stops a Hyper-V virtual machine."""
        suffix = " -TurnOff" if force else ""
        cmd = f"Stop-VM -Name '{vm_name}'{suffix}"
        return self._run_ps(cmd)

    def run_script_in_guest(self, vm_name: str, script_path: str, credentials: Optional[dict] = None) -> OrchestrationResult:
        """Runs a script inside the guest VM using PowerShell Direct (HKS)."""
        # Note: This requires the VM to be running and have guest services enabled.
        # We assume 'Administrator' access for the lab environment.
        
        # For simplicity in this scaffold, we'll use Invoke-Command with the local script content
        try:
            with open(script_path, 'r') as f:
                script_content = f.read()
            
            # Escape single quotes for PowerShell
            escaped_content = script_content.replace("'", "''")
            
            # Using -VMName uses PowerShell Direct (no network required, just guest services)
            cmd = f"Invoke-Command -VMName '{vm_name}' -ScriptBlock {{ {escaped_content} }} -Credential (Get-Credential)" # Credential handling would be more robust in production
            
            # For the lab, we'll likely use a pre-configured PSCredential object or trust
            # Let's simplify for the initial controller:
            cmd = f"Invoke-Command -VMName '{vm_name}' -ScriptBlock {{ {escaped_content} }}"
            
            return self._run_ps(cmd)
        except Exception as e:
            return OrchestrationResult(success=False, output="", error=f"Failed to read script file: {str(e)}")

    def copy_file_to_guest(self, vm_name: str, source: str, destination: str) -> OrchestrationResult:
        """Copies a file from the host to the guest VM."""
        # Copy-Item -ToSession requires a session, but Copy-Item -VMName works in newer PS versions
        cmd = f"Copy-Item -Path '{source}' -Destination '{destination}' -VMName '{vm_name}'"
        return self._run_ps(cmd)

    def get_vm_ip(self, vm_name: str) -> OrchestrationResult:
        """Retrieves the primary IPv4 address of a VM from Hyper-V Guest Services."""
        # Filter for IPv4 addresses (containing dots)
        cmd = f"(Get-VMNetworkAdapter -VMName '{vm_name}').IPAddresses | Where-Object {{ $_ -like '*.*' }} | Select-Object -First 1"
        return self._run_ps(cmd)

    def wait_for_guest_readiness(self, vm_name: str, timeout_seconds: int = 60) -> bool:
        """Polls the VM's heartbeat and network status until it's ready."""
        import time
        start_time = time.time()
        
        if self.dry_run:
            return True

        while time.time() - start_time < timeout_seconds:
            # Check for a non-empty IPv4 address
            res = self.get_vm_ip(vm_name)
            if res.success and res.output:
                logger.info(f"VM {vm_name} is ready with IP: {res.output}")
                return True
            time.sleep(2)
        
        logger.warning(f"Timed out waiting for VM {vm_name} to report an IP address.")
        return False
