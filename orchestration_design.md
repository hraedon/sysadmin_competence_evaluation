# Sysadmin Competency Assessment Platform — Orchestration Layer Design

## Exercise Taxonomy by Delivery Mode

Every exercise maps to exactly one primary mode.

### Mode A: Artifact Presentation + Written Response
The learner analyzes a static artifact (script, log, etc.). AI evaluates reasoning against the rubric.
**No lab required.**

### Mode B: Written Production (Commission)
The learner produces a specification or plan. AI evaluates completeness and quality.
**No lab required.**

### Mode C: Socratic/Branching Dialogue
AI-guided interaction with staged information reveals. AI tracks diagnostic efficiency.
**No lab required.**

### Mode D: Transcript Analysis (Theory of Mind)
Analysis of communication transcripts for social/organizational reasoning.
**No lab required.**

### Mode E: Hands-On Lab
Learner operates in live VMs. Validation via state checks.
**Lab environment required.**

---

## Lab Orchestration (Phase 2)

The lab environment uses a pluggable hypervisor backend for virtualization and Apache Guacamole for browser-based access.

### Supported Platforms

| Platform | Orchestrator | VM Management | Guest Operations | Status |
|----------|-------------|---------------|------------------|--------|
| **Hyper-V** | `HyperVOrchestrator` | WinRM/PowerShell remoting | PowerShell Direct (VMBus) | Production |
| **Proxmox** | `ProxmoxOrchestrator` | REST API | QEMU Guest Agent | Stub (dry-run only) |

### Orchestrator Interface

All platform backends implement the `Orchestrator` abstract base class (`orchestrator_base.py`):

```python
class Orchestrator(ABC):
    async def revert_to_checkpoint(vm_name, checkpoint_name) -> OrchestrationResult
    async def start_vm(vm_name) -> OrchestrationResult
    async def stop_vm(vm_name, force=False) -> OrchestrationResult
    async def get_vm_ip(vm_name) -> OrchestrationResult
    async def test_guest_connectivity(vm_name) -> OrchestrationResult
    async def get_vm_state(vm_name) -> OrchestrationResult
    async def run_script_in_guest(vm_name, script_path) -> OrchestrationResult
    async def copy_file_to_guest(vm_name, source, destination) -> OrchestrationResult
    async def wait_for_guest_readiness(vm_name, timeout, callback) -> bool  # default impl
```

Platform selection is controlled by the `LAB_PLATFORM` environment variable (`hyper-v` or `proxmox`).

### Components
1. **Lab Controller (FastAPI)**: A Python service that orchestrates VMs and Guacamole.
2. **Orchestrator Backend**: Platform-specific VM management (selected at startup).
3. **Guacamole REST Client**: Programmatically creates temporary connections for each session.

### Provisioning Flow
1. Frontend calls `POST /lab/provision/{scenario_id}`.
2. Controller selects an available environment with matching capabilities.
3. Controller reverts VMs to the baseline snapshot/checkpoint.
4. Controller starts VMs and waits for guest readiness.
5. Controller runs provisioning scripts inside the guest.
6. Controller creates a Guacamole connection and returns the session token.
7. Frontend polls `GET /lab/session/{token}` and embeds Guacamole iframe when ready.

### Validation Flow
1. Frontend calls `POST /lab/verify/{session_id}`.
2. Controller runs validation scripts inside the guest VMs.
3. Returns a three-state result: `correct | workaround | incomplete` per finding.
4. Results are persisted to the session and included in AI evaluation context (ARCH-17).

---

## Environment Configuration

`environments.yaml` defines the VM pool:

```yaml
environments:
  - id: env-windows-01
    platform: hyper-v          # or proxmox
    vms: ["LabDC01", "LabServer01"]
    guac_target_vm: "LabServer01"
    guac_protocol: "rdp"
    capabilities: ["windows-server", "windows-domain"]
    status: "available"
```

For Proxmox environments, a `vm_id_map` field maps friendly names to VMIDs:

```yaml
  - id: env-proxmox-linux-01
    platform: proxmox
    vms: ["LinuxLab01"]
    vm_id_map: {"LinuxLab01": "101"}
    guac_target_vm: "LinuxLab01"
    guac_protocol: "ssh"
    capabilities: ["linux"]
    status: "available"
```

---

## Administrative Controls

### Admin Panel Requirements
- **Session Oversight**: View all active lab sessions, including user ID, scenario, and time remaining.
- **Environment Status**: Monitor the health and state of all configured environments.
- **Force Termination**: Manually end any session, triggering teardown and revert.
- **Log Access**: Quick access to lab-controller logs for troubleshooting.

---

## AI Evaluation Architecture

Evaluations are performed by a shared core module (`core/evaluator.js`) and its Python mirror (`app/evaluator.py`).

### System Prompt Assembly
- **Artifacts**: Resolved from the active mode's `artifact_file`.
- **Findings**: Includes `description` and `miss_signal` (unless `compactRubric` is set).
- **Learning Notes**: Explicitly excluded from the evaluator prompt to prevent answer leakage.
- **Lab State**: For Mode E, verification results are included as `[LAB VERIFICATION STATE]` context.

### Calibration
Calibration is the process of testing rubrics against synthetic responses.
- **Pass Tolerance**: +/- 0.5 levels.
- **Tools**: `calibration/run.mjs` supports domain/scenario/level filtering and surfaces evaluator narratives on failure.
