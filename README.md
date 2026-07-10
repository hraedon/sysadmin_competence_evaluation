# Sysadmin Competency Assessment Platform

An interactive assessment platform built around the Modern Systems Administration Competency Map — a 14-domain framework with ~60 exercises testing applied reasoning rather than rote knowledge. The platform presents realistic scenarios (logs, scripts, change records, configuration artifacts), collects written responses, and evaluates them with an AI against calibrated rubrics.

**Live:** https://learning.hraedon.com

---

## What it tests

The competency map divides sysadmin work into 14 domains. Each domain has exercises at Levels 1–4 (labels below are the map's canonical taxonomy; each domain names its own variant, e.g. "Script Audit", "Change Commission"):

| Level | Label | What it means |
|-------|-------|---------------|
| 1 | Literacy | Can read and describe — given a config, script, or log, explain what it does and what state it implies |
| 2 | Audit | Can identify risks, gaps, and failure modes, and assess severity accurately |
| 3 | Commission | Can specify requirements well enough to direct production work and evaluate what comes back |
| 4 | Adaptation | Can make targeted, understood modifications — or exercise the domain's expert judgment (arbitration/design) |

**Canonical source:** the map lives in [`curriculum/`](curriculum/) as markdown, one file per domain — the `.docx` is a rendered artifact (`scripts/build_map.sh` → `dist/`). Domain cross-references are checked by `scripts/check_map_refs.py` in CI. Domain numbers are stable IDs: new domains append, renumbering is prohibited (see `plans/001`).

The exercises test reasoning, not recall. A candidate who has memorized the right answer to a known scenario can still fail if they cannot identify *why* the evidence points that direction.

---

## Repository structure

```
core/                    Shared JavaScript evaluator logic
scenarios/               Exercise definitions and artifacts (58 scenarios across d01-d14)

  d01-d11/               Standard technical domains
  d12/                   Linux Administration (3 synthesis scenarios)
  d13/                   Cross-domain Synthesis
  d14/                   Theory of Mind & Communication (5 scenarios)
  d15/                   Directing AI Agents (20 scenarios, synced from agentic-onboarding)

platform/
  frontend/              React + Vite SPA
  lab-controller/        FastAPI (Python) Hyper-V/Guacamole orchestrator
  k8s/                   Kubernetes manifests
  guacamole/             Lab environment user-plane

calibration/
  run.mjs                Node.js calibration harness
```

### Schema V2.0
All scenarios use **Schema V2.0**, which features a unified `findings` list and support for hands-on lab (Mode E) provisioning and verification.

---

## How the evaluation works

Evaluations are performed by a shared core module (`core/evaluator.js`). It assembles a system prompt from the scenario's YAML rubric and calls the configured AI provider (Sonnet 4.6 or local LLM). 

### Calibration
Every scenario must pass the calibration harness before deployment. The harness runs synthetic responses at each level through the evaluator and verifies that the returned level matches the expected level within a 0.5 margin.

**Current Status:** 60 scenarios (d01-d14) + 20 d15 scenarios synced from [agentic-onboarding](../agentic-onboarding) = 80 total. Calibrated on Sonnet 4.6.

---

## Hands-On Labs (Phase 2)

The platform supports live VM environments via:
1. **Lab Controller**: A Python service that orchestrates Hyper-V checkpoints and VM state.
2. **Guacamole**: Provides browser-based RDP/SSH access via a REST API.
3. **Automated Verification**: Validation scripts check environment state and return three-state results (`correct | workaround | incomplete`).
