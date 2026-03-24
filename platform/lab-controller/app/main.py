from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import yaml
import os
from pathlib import Path
from .orchestrator import HyperVOrchestrator
from .guacamole import GuacamoleClient
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    guacamole_url: str = "http://localhost:8080/guacamole"
    guacamole_username: str = ""
    guacamole_password: str = ""
    dry_run: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
app = FastAPI(title="Sysadmin Competency Lab Controller")

import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

orchestrator = HyperVOrchestrator(dry_run=settings.dry_run)
guac_client = GuacamoleClient(
    settings.guacamole_url, 
    settings.guacamole_username, 
    settings.guacamole_password
)

# ... (Models remain same)
class LabAction(BaseModel):
    action: str
    target: Optional[str] = None
    file: Optional[str] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    name: Optional[str] = None

class LabConfig(BaseModel):
    provisioning: List[LabAction] = []
    cleanup: List[LabAction] = []

class LabModeE(BaseModel):
    type: str
    platform: str
    checkpoint: str
    vm_targets: List[str]
    connection_type: str
    instructions: str
    config: Optional[LabConfig] = None

class VerificationResult(BaseModel):
    finding_id: str
    status: str  # correct | workaround | incomplete
    detail: str

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/lab/provision/{scenario_id}")
async def provision_lab(scenario_id: str, background_tasks: BackgroundTasks):
    # Path to scenarios (assuming relative to project root)
    scenario_path = Path(f"../../scenarios/{scenario_id.replace('-', '/')}/scenario.yaml")
    
    if not scenario_path.exists():
        # Fallback search if path doesn't exist
        raise HTTPException(status_code=404, detail=f"Scenario {scenario_id} not found.")

    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)

    mode_e = scenario.get('presentation', {}).get('modes', {}).get('E')
    if not mode_e:
        raise HTTPException(status_code=400, detail="Scenario does not support Mode E (Lab)")

    checkpoint = mode_e.get('checkpoint')
    vm_targets = mode_e.get('vm_targets', [])
    config = mode_e.get('config', {})
    provisioning_actions = config.get('provisioning', [])

    logger.info(f"Provisioning Lab: {scenario_id}")

    # 1. Revert VMs to baseline
    for vm in vm_targets:
        logger.info(f"Reverting {vm} to {checkpoint}")
        res = orchestrator.revert_to_checkpoint(vm, checkpoint)
        if not res.success:
            raise HTTPException(status_code=500, detail=f"Failed to revert {vm}: {res.error}")

    # 2. Start VMs
    for vm in vm_targets:
        logger.info(f"Starting {vm}")
        res = orchestrator.start_vm(vm)
        if not res.success:
            raise HTTPException(status_code=500, detail=f"Failed to start {vm}: {res.error}")

    # 3. Execute Provisioning Actions (Scripts/File Copies)
    # TODO: Wait for VMs to be ready (IP address / Guest Services)
    for action in provisioning_actions:
        target = action.get('target')
        act_type = action.get('action')
        
        if act_type == "run_script":
            script_file = action.get('file')
            # Resolve script path relative to scenario dir
            script_path = scenario_path.parent / script_file
            res = orchestrator.run_script_in_guest(target, str(script_path))
        elif act_type == "copy_file":
            src = scenario_path.parent / action.get('source')
            dest = action.get('destination')
            res = orchestrator.copy_file_to_guest(target, str(src), dest)
        
        if not res.success:
            logger.error(f"Provisioning action failed on {target}: {res.error}")
            # We might not want to hard-fail here, but log it

    # 4. Create Guacamole Connection
    # For now, we assume the first VM is the primary target for RDP/SSH
    primary_vm = vm_targets[0] if vm_targets else "unknown"
    # Parameters would normally come from an environment map (IPs etc)
    # For this scaffold, we'll use a placeholder or lookup logic
    conn_params = {
        "hostname": primary_vm, # In prod, this would be an IP address
        "username": "Administrator",
        "password": "" # Should be retrieved from a secure vault or session context
    }
    
    guac_url = await guac_client.create_connection(
        name=f"Lab: {scenario_id}",
        protocol=mode_e.get('connection_type', 'rdp'),
        parameters=conn_params
    )

    return {
        "status": "ready",
        "scenario_id": scenario_id,
        "guacamole_url": guac_url,
        "instructions": mode_e.get('instructions')
    }

@app.post("/lab/verify/{session_id}")
async def verify_lab(session_id: str):
    # TODO: Implement actual verification via scripts
    # This will return the 3-state validation result required by CLAUDE.md
    return [
        VerificationResult(
            finding_id="example_finding", 
            status="correct", 
            detail="Service is running with the correct security context."
        )
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
