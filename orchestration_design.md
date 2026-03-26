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

## Scenario Definition (Schema V2.0)

See `scenario_specification_v2.md` for the full schema. Key features:
- **Unified Findings**: All rubric items in a single `findings` list with `type: critical|secondary`.
- **Mode-Specific Presentation**: Instructions and artifacts nested under `presentation.modes.[A|B|C|D|E]`.
- **Lab Configuration**: Provisioning and cleanup steps defined within the `E` mode block.

---

## Lab Orchestration (Phase 2)

The lab environment uses Hyper-V for virtualization and Apache Guacamole for browser-based access.

### Components
1. **Lab Controller (FastAPI)**: A Python service that orchestrates Hyper-V and Guacamole.
2. **Hyper-V Orchestrator**: Executes PowerShell cmdlets (`Restore-VMSnapshot`, `Start-VM`, `Invoke-Command`) to prepare the environment.
3. **Guacamole REST Client**: Programmatically creates temporary connections for each session.

### Provisioning Flow
1. Frontend calls `POST /lab/provision/{scenario_id}`.
2. Controller reverts VMs to the baseline checkpoint.
3. Controller starts VMs and runs provisioning scripts.
4. Controller creates a Guacamole connection and returns the URL.
5. Frontend embeds Guacamole in an iframe.

### Validation Flow
1. Frontend calls `POST /lab/verify/{session_id}`.
2. Controller runs validation scripts inside the guest VMs.
3. Returns a three-state result: `correct | workaround | incomplete` per finding.

---

## AI Evaluation Architecture

Evaluations are performed by a shared core module (`core/evaluator.js`).

### System Prompt Assembly
- **Artifacts**: Resolved from the active mode's `artifact_file`.
- **Findings**: Includes `description` and `miss_signal` (unless `compactRubric` is set).
- **Learning Notes**: Explicitly excluded from the evaluator prompt to prevent answer leakage.

### Calibration
Calibration is the process of testing rubrics against synthetic responses.
- **Pass Tolerance**: +/- 0.5 levels.
- **Tools**: `calibration/run.mjs` supports domain/scenario/level filtering and surfaces evaluator narratives on failure.
