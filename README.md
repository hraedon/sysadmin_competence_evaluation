# Sysadmin Competency Assessment Platform

An interactive assessment platform built around the Modern Systems Administration Competency Map — a 14-domain framework with ~60 exercises testing applied reasoning rather than rote knowledge. The platform presents realistic scenarios (logs, scripts, change records, configuration artifacts), collects written responses, and evaluates them with an AI against calibrated rubrics.

**Live:** https://learning.hraedon.com

---

## What it tests

The competency map divides sysadmin work into 14 domains. Each domain has exercises at Levels 1–4:

| Level | Label | What it means |
|-------|-------|---------------|
| 1 | Awareness | Read the artifact and describe what it is doing |
| 2 | Application | Identify risks, gaps, and violations |
| 3 | Analysis | Specify what should be done — write the change plan, escalation, or spec |
| 4 | Adaptation | Reason under uncertainty, calibrate severity, handle novel edge cases |

The exercises test reasoning, not recall. A candidate who has memorized the right answer to a known scenario can still fail if they cannot identify *why* the evidence points that direction.

---

## Repository structure

```
core/                    Shared JavaScript evaluator logic
scenarios/               Exercise definitions and artifacts (53 scenarios)

  d01-d11/               Standard technical domains
  d12/                   Linux Administration (3 synthesis scenarios)
  d13/                   Cross-domain Synthesis
  d14/                   Theory of Mind & Communication (5 scenarios)

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

**Current Status:** 53 scenarios calibrated — 100% pass rate on Sonnet 4.6.

---

## Hands-On Labs (Phase 2)

The platform supports live VM environments via:
1. **Lab Controller**: A Python service that orchestrates Hyper-V checkpoints and VM state.
2. **Guacamole**: Provides browser-based RDP/SSH access via a REST API.
3. **Automated Verification**: Validation scripts check environment state and return three-state results (`correct | workaround | incomplete`).
