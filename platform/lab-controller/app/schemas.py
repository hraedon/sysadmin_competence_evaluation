from typing import List, Optional, Dict, Any
import datetime
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    guacamole_url: str = "http://localhost:8080/guacamole"
    guacamole_username: str = ""
    guacamole_password: str = ""
    scenarios_dir: str = "/scenarios"
    environments_config: str = "environments.yaml"
    session_timeout_minutes: int = 120
    max_session_hours: int = 4
    provisioning_timeout_seconds: int = 600
    dry_run: bool = True
    # Hyper-V host credentials for WinRM remoting (used by HyperVOrchestrator)
    hyperv_host: str = "mvmhyperv02.ad.hraedon.com" # INFRA-02: was hardcoded
    hyperv_username: str = "svc_claude@ad.hraedon.com"
    hyperv_password: str = ""
    # Guest OS credentials for PowerShell Direct (lab domain admin)
    hyperv_guest_username: str = "ad.labdomain.dev\\claude"
    hyperv_guest_password: str = ""
    controller_api_key: str = "dev-key-change-me"
    anthropic_api_key: str = ""
    # Reconciler settings
    reconcile_interval_minutes: int = 5
    fault_auto_retry_delay_minutes: int = 10
    fault_max_auto_retries: int = 2
    # Verified 2026-03-28: all Hyper-V VMs (LabServer01, LabDC01, LabLinux01) use
    # "Baseline Checkpoint" as the snapshot name. This must match exactly.
    baseline_checkpoint_name: str = "Baseline Checkpoint"
    # JWT auth settings
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    model_config = {
        "env_file": ".env"
    }

settings = Settings()

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

class ProvisionRequest(BaseModel):
    user_id: str
    capabilities: List[str] = []

class ProvisionResponse(BaseModel):
    status: str
    session_token: str
    environment_id: str
    guacamole_url: Optional[str] = None
    expires_at: datetime.datetime
    instructions: str

class VerificationResult(BaseModel):
    finding_id: str
    status: str  # correct | workaround | incomplete
    detail: str

class EvaluateRequest(BaseModel):
    scenario: Dict[str, Any]
    artifactContent: Optional[str] = None
    responseText: str
    model: Optional[str] = None
    coachMode: bool = False
    coachRound: int = 0
    coachHistory: List[Dict[str, str]] = []
    compactRubric: bool = False
