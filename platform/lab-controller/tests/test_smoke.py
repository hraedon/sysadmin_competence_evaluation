import asyncio
import os
import sys
import pytest
from dotenv import load_dotenv

# Add app to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from app.orchestrator import HyperVOrchestrator

load_dotenv()

@pytest.mark.anyio
async def test_hyperv_winrm_connectivity():
    """Verifies basic WinRM connectivity to the Hyper-V host."""
    host = os.getenv("HYPERV_HOST")
    user = os.getenv("HYPERV_USERNAME")
    pw = os.getenv("HYPERV_PASSWORD")

    if not all([host, user, pw]):
        pytest.skip("HYPERV credentials not set in .env")

    orch = HyperVOrchestrator(host, user, pw, dry_run=False)
    res = await orch.get_vm_state("LabDC01") 
    assert res.success, f"WinRM connectivity failed: {res.error}"

@pytest.mark.anyio
async def test_powershell_direct_logic():
    """
    Verifies the New-PSSession / PowerShell Direct logic.
    Requires at least one VM to be running.
    """
    host = os.getenv("HYPERV_HOST")
    user = os.getenv("HYPERV_USERNAME")
    pw = os.getenv("HYPERV_PASSWORD")
    guest_user = os.getenv("HYPERV_GUEST_USERNAME")
    guest_pw = os.getenv("HYPERV_GUEST_PASSWORD")

    if not all([host, user, pw, guest_user, guest_pw]):
        pytest.skip("Full HYPERV/GUEST credentials not set in .env")

    orch = HyperVOrchestrator(host, user, pw, guest_user, guest_pw, dry_run=False)
    
    # Check if LabDC01 is running
    res = await orch.get_vm_state("LabDC01")
    if not res.success or res.output.strip() != "Running":
        pytest.skip("LabDC01 is not running; skipping guest connectivity test")

    res = await orch.test_guest_connectivity("LabDC01")
    assert res.success, f"PowerShell Direct logic failed: {res.error}"
