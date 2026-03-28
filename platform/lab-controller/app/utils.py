import re
from pathlib import Path
from fastapi import HTTPException
from .schemas import settings

def sanitize_scenario_id(scenario_id: str) -> str:
    if not re.match(r'^[a-z0-9\-]+$', scenario_id):
        raise HTTPException(status_code=400, detail="Invalid scenario_id format.")
    return scenario_id

def resolve_scenario_path(scenario_id: str) -> Path:
    scenarios_dir = Path(settings.scenarios_dir).resolve()
    
    # Expected format: dXX-scenario-name
    # Maps to: dXX/scenario_name/scenario.yaml
    parts = scenario_id.split('-', 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid scenario_id format. Expected dXX-name.")
    
    domain_dir = parts[0]
    scenario_folder = parts[1].replace('-', '_')
    
    scenario_path = (scenarios_dir / domain_dir / scenario_folder / "scenario.yaml").resolve()
    
    if not str(scenario_path).startswith(str(scenarios_dir)):
        raise HTTPException(status_code=400, detail="Invalid scenario_id path.")
    return scenario_path
