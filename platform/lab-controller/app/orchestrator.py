import asyncio
import logging
import os
from typing import Optional
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OrchestrationResult(BaseModel):
    success: bool
    output: str
    error: Optional[str] = None

class HyperVOrchestrator:
    """
    Runs Hyper-V management commands on a remote host via WinRM (PowerShell Core).

    All non-dry-run operations tunnel through Invoke-Command -ComputerName to
    reach the Hyper-V host; guest-level operations add a second hop using
    PowerShell Direct (-VMName) running on that host.

    Credentials are passed to the pwsh subprocess via environment variables
    (HYPERV_PASSWORD, HYPERV_GUEST_PASSWORD), not embedded in the command
    string. They are referenced inside the PowerShell script via $env:VAR.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        guest_username: str = "",
        guest_password: str = "",
        dry_run: bool = True,
    ):
        self.host = host
        self.username = username
        self.password = password
        self.guest_username = guest_username
        self.guest_password = guest_password
        self.dry_run = dry_run

    def _remote_wrap(self, inner_command: str) -> str:
        """Wraps an inner PowerShell command to execute on the Hyper-V host via WinRM."""
        esc_user = self.username.replace("'", "''")
        esc_host = self.host.replace("'", "''")
        # Pass the Hyper-V host password via environment variable (local to pwsh process).
        # Pass the Guest OS password via -ArgumentList so it's available inside the remote ScriptBlock.
        return (
            f"$ErrorActionPreference = 'Stop'; "
            f"$escPw = $env:HYPERV_PASSWORD.Replace(\"'\", \"''\"); "
            f"$cred = [System.Management.Automation.PSCredential]::new("
            f"'{esc_user}', (ConvertTo-SecureString $env:HYPERV_PASSWORD -AsPlainText -Force)); "
            f"Invoke-Command -ComputerName '{esc_host}' -Credential $cred -Authentication Negotiate "
            f"-ScriptBlock {{ param($GUEST_PW) {inner_command} }} "
            f"-ArgumentList $env:HYPERV_GUEST_PASSWORD"
        )

    async def _run_ps(self, command: str) -> OrchestrationResult:
        """Executes a PowerShell command via pwsh (PowerShell Core for Linux containers)."""
        if self.dry_run:
            logger.info(f"[DRY RUN] PS command ({len(command)} chars)")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="Dry run success")

        env = os.environ.copy()
        env["HYPERV_PASSWORD"] = self.password
        env["HYPERV_GUEST_PASSWORD"] = self.guest_password

        try:
            process = await asyncio.create_subprocess_exec(
                "pwsh", "-NoProfile", "-NonInteractive", "-Command", command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return OrchestrationResult(success=True, output=stdout.decode().strip())
            else:
                return OrchestrationResult(
                    success=False,
                    output=stdout.decode().strip(),
                    error=stderr.decode().strip(),
                )
        except Exception as e:
            return OrchestrationResult(success=False, output="", error=str(e))

    async def revert_to_checkpoint(self, vm_name: str, checkpoint_name: str) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Reverting {vm_name} to '{checkpoint_name}'")
            await asyncio.sleep(2)
            return OrchestrationResult(success=True, output="Dry run success")
        inner = f"Restore-VMSnapshot -VMName '{vm_name}' -Name '{checkpoint_name}' -Confirm:$false"
        return await self._run_ps(self._remote_wrap(inner))

    async def start_vm(self, vm_name: str) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Starting {vm_name}")
            await asyncio.sleep(1)
            return OrchestrationResult(success=True, output="Dry run success")
        inner = f"Start-VM -Name '{vm_name}'"
        return await self._run_ps(self._remote_wrap(inner))

    async def stop_vm(self, vm_name: str, force: bool = False) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Stopping {vm_name} (force={force})")
            await asyncio.sleep(1)
            return OrchestrationResult(success=True, output="Dry run success")
        suffix = " -TurnOff" if force else ""
        inner = f"Stop-VM -Name '{vm_name}'{suffix}"
        return await self._run_ps(self._remote_wrap(inner))

    async def get_vm_ip(self, vm_name: str) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Getting IP for {vm_name}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="192.168.100.15")
        inner = (
            f"(Get-VMNetworkAdapter -VMName '{vm_name}').IPAddresses"
            f" | Where-Object {{ $_ -like '*.*' }}"
            f" | Select-Object -First 1"
        )
        return await self._run_ps(self._remote_wrap(inner))

    async def test_guest_connectivity(self, vm_name: str) -> OrchestrationResult:
        """Tests that the guest OS is responsive via PowerShell Direct."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Testing connectivity for {vm_name}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="OK")
        cred_snippet = self._guest_cred_ps() if self.guest_username else ""
        inner = (
            f"{cred_snippet}"
            f"Invoke-Command -VMName '{vm_name}'"
            f"{' -Credential $guestCred' if self.guest_username else ''}"
            f" -ScriptBlock {{ 'OK' }}"
        )
        return await self._run_ps(self._remote_wrap(inner))

    async def get_vm_state(self, vm_name: str) -> OrchestrationResult:
        """Returns the current power state of a VM as reported by Hyper-V.

        Possible values: Running, Off, Saved, Paused, Starting, Stopping, Saving,
        Pausing, Resuming, Reset, CheckpointApplying, Unknown.

        Used by the reconciler to detect orphan VMs (Running while environment
        shows 'available').  Does not enter the guest — queries the Hyper-V host only.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Getting state for {vm_name}")
            return OrchestrationResult(success=True, output="Off")
        inner = f"(Get-VM -Name '{vm_name}').State.ToString()"
        return await self._run_ps(self._remote_wrap(inner))

    async def wait_for_guest_readiness(self, vm_name: str, timeout_seconds: int = 300, on_connectivity_phase=None) -> bool:
        """Polls the VM for an IP address, then confirms with a connectivity test.

        Args:
            on_connectivity_phase: optional async callback invoked when transitioning
                from IP-wait to connectivity-test phase.
        """
        start_time = asyncio.get_running_loop().time()
        # Phase 1: wait for IP address (fast check)
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

    def _guest_cred_ps(self) -> str:
        """Returns a PowerShell snippet that creates $guestCred from guest credentials."""
        esc_user = self.guest_username.replace("'", "''")
        # GUEST_PW is passed via -ArgumentList in _remote_wrap and available in the remote ScriptBlock.
        return (
            f"$guestCred = [System.Management.Automation.PSCredential]::new("
            f"'{esc_user}', (ConvertTo-SecureString $GUEST_PW -AsPlainText -Force)); "
        )

    async def run_script_in_guest(self, vm_name: str, script_path: str) -> OrchestrationResult:
        """
        Runs a local script file inside the guest VM using PowerShell Direct.

        Instead of injecting script content into a string (which is fragile),
        this method copies the script file to the guest's C:\Windows\Temp
        directory and then executes it.
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Running script in {vm_name}: {script_path}")
            await asyncio.sleep(1)
            return OrchestrationResult(
                success=True,
                output='{"status":"correct","detail":"Dry run verification passed."}'
            )

        if not os.path.exists(script_path):
            return OrchestrationResult(success=False, output="", error=f"Script not found: {script_path}")

        # 1. Copy script to guest
        filename = os.path.basename(script_path)
        guest_path = f"C:\\Windows\\Temp\\{filename}"
        copy_res = await self.copy_file_to_guest(vm_name, script_path, guest_path)
        if not copy_res.success:
            return copy_res

        # 2. Execute script in guest
        try:
            cred_snippet = self._guest_cred_ps() if self.guest_username else ""
            inner = (
                f"{cred_snippet}"
                f"Invoke-Command -VMName '{vm_name}'"
                f"{' -Credential $guestCred' if self.guest_username else ''}"
                f" -ScriptBlock {{ & '{guest_path}' }}"
            )
            return await self._run_ps(self._remote_wrap(inner))
        except Exception as e:
            return OrchestrationResult(success=False, output="", error=str(e))

    async def copy_file_to_guest(self, vm_name: str, source: str, destination: str) -> OrchestrationResult:
        if self.dry_run:
            logger.info(f"[DRY RUN] Copying {source} → {vm_name}:{destination}")
            await asyncio.sleep(0.5)
            return OrchestrationResult(success=True, output="Dry run success")
        cred_snippet = self._guest_cred_ps() if self.guest_username else ""
        inner = (
            f"{cred_snippet}"
            f"Copy-Item -Path '{source}' -Destination '{destination}'"
            f" -VMName '{vm_name}'"
            f"{' -Credential $guestCred' if self.guest_username else ''}"
        )
        return await self._run_ps(self._remote_wrap(inner))
