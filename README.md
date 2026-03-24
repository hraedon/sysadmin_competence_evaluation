# Sysadmin Competency Assessment Platform

An interactive assessment platform built around the Modern Systems Administration Competency Map — a 14-domain framework with ~60 exercises testing applied reasoning rather than rote knowledge. The platform presents realistic scenarios (logs, scripts, change records, configuration artifacts), collects written responses, and evaluates them with an AI against calibrated rubrics.

**Live:** https://learning.hraedon.com

---

## What it tests

The competency map divides sysadmin work into 14 domains — scripting, identity and hybrid IAM, networking, PKI, storage, compute, cloud, security reasoning, change management, backup and recovery, log reading, Linux, cross-domain synthesis, and Theory of Mind (communication). Each domain has exercises at Levels 1–4:

| Level | Label | What it means |
|-------|-------|---------------|
| 1 | Awareness | Read the artifact and describe what it is doing |
| 2 | Application | Identify risks, gaps, and violations |
| 3 | Analysis | Specify what should be done — write the change plan, escalation, or spec |
| 4 | Adaptation | Reason under uncertainty, calibrate severity, handle novel edge cases |

The exercises test reasoning, not recall. A candidate who has memorized the right answer to a known scenario can still fail if they cannot identify *why* the evidence points that direction, or what a different artifact would require them to reconsider.

---

## Repository structure

```
scenarios/               Exercise definitions and artifacts
  d01/                   Domain 1 — Scripting & Automation (5 scenarios)
  d02/                   Domain 2 — Identity & Hybrid IAM (8 scenarios)
  d03/                   Domain 3 — Networking (5 scenarios)
  d04/                   Domain 4 — PKI & Certificates (5 scenarios)
  d05/                   Domain 5 — Storage Architecture (5 scenarios)
  d06/                   Domain 6 — Compute & Virtualisation (1 scenario)
  d07/                   Domain 7 — Cloud Infrastructure (2 scenarios)
  d08/                   Domain 8 — Security Reasoning (1 scenario)
  d09/                   Domain 9 — Change Management (4 scenarios)
  d10/                   Domain 10 — Backup & Recovery (1 scenario)
  d11/                   Domain 11 — Log Reading & Diagnosis (3 scenarios)
  d13/                   Domain 13 — Cross-domain Synthesis (3 scenarios)
  d14/                   Domain 14 — Theory of Mind & Communication (2 scenarios)

platform/
  frontend/              React + Vite + Tailwind SPA
  k8s/                   Kubernetes manifests (namespace, deployment, service, ingress)
  guacamole/             Lab environment user-plane (Apache Guacamole + guacd)
  Dockerfile             Builds nginx container serving the static React app
  build_notes.md         Architecture decisions and session changelog

calibration/
  run.mjs                Node.js calibration harness
  README.md              Calibration procedure and troubleshooting guide
```

Each scenario directory contains:
- `scenario.yaml` — rubric, level indicators, difficulty rating, and artifact path
- One artifact file (PowerShell script, log extract, config listing, etc.)
- `response_level_1.txt` through `response_level_4.txt` — synthetic responses for calibration

### Schema V2
New scenarios (Domain 14 onwards) use **Schema V2**, which features a unified `findings` list and support for future lab-based verification. The platform remains backward-compatible with V1 scenarios.

---

## How the evaluation works

The platform assembles an AI evaluator system prompt from the scenario's YAML rubric and calls the configured AI provider. The evaluator returns a structured result including level, caught/missed findings, and a diagnostic `gap` field.

### Local AI Proxy
To maintain privacy and bypass "Private Network Access" browser restrictions, the platform uses a pod-based reverse proxy at `/llm-proxy/`. This allows the browser to communicate securely with your local LLM (e.g., LM Studio or Ollama) without exposing internal IP addresses.

---

## Running locally

```bash
cd platform/frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173`. By default, the platform connects to the local proxy in production or your internal IP in development. To use Anthropic or OpenAI, open Settings and configure the provider and key.

---

## Calibration

Every scenario must pass calibration before being used with real learners. The harness runs synthetic responses at each level through the evaluator and checks that the returned level matches the expected level.

```bash
cd calibration
npm install
node run.mjs # Local Qwen 80B default
```

**Current calibration status:** 45 scenarios calibrated — 174/180 passing (96.6%). All 11 currently authored domains have calibrated content.

---

## Deployment & CI/CD

The platform is deployed to a K8s cluster via GitHub Actions.
- **Push to main**: Triggers a Docker build and push to GHCR.
- **Rollout**: The workflow automatically triggers a `kubectl rollout restart` to ensure the cluster pulls the latest image. 
- **Secret**: Requires a base64-encoded `KUBECONFIG` secret in GitHub.

---

## Lab Environment (In Progress)

The "User Plane" for hands-on labs is provided by **Apache Guacamole** running in the cluster, with a dedicated Postgres backend. Future phases will integrate the "Control Plane" (Orchestrator) to automate Hyper-V snapshot management.
