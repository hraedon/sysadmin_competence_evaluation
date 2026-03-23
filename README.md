# Sysadmin Competency Assessment Platform

An interactive assessment platform built around the Modern Systems Administration Competency Map — a 14-domain framework with ~60 exercises testing applied reasoning rather than rote knowledge. The platform presents realistic scenarios (logs, scripts, change records, configuration artifacts), collects written responses, and evaluates them with an AI against calibrated rubrics.

**Live:** https://assessment.k8s.hraedon.com

---

## What it tests

The competency map divides sysadmin work into 14 domains — scripting, identity and hybrid IAM, networking, PKI, storage, compute, cloud, security reasoning, change management, backup and recovery, log reading, Linux, cross-domain synthesis, and organizational effectiveness. Each domain has exercises at Levels 1–4:

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

platform/
  frontend/              React + Vite + Tailwind SPA
  k8s/                   Kubernetes manifests (namespace, deployment, service, ingress)
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

---

## How the evaluation works

The platform assembles an AI evaluator system prompt from the scenario's YAML rubric (critical findings, secondary findings, miss signals, level indicators) and calls the configured AI provider. The evaluator returns a structured result:

```json
{
  "level": 2,
  "confidence": "high",
  "caught": ["finding_id_1"],
  "missed": ["finding_id_2"],
  "unlisted": [],
  "severity_calibration": "accurate",
  "gap": "Identifies the root cause but does not explain why FQDN and IP connections behave differently.",
  "narrative": "..."
}
```

Level estimates are 1–4. The `gap` field explains specifically what distinguishes the candidate's response from the next level — it is diagnostic, not merely evaluative.

### Evaluator modes

**Strict Auditor** — shows the full evaluation immediately after submission: level, caught/missed findings, gap description, and an explanation link on each missed finding that surfaces the `learning_note` for that concept.

**Socratic Coach** — withholds the full result and asks a Socratic question pointing at specific artifact evidence for the primary missed finding. Runs up to three coaching rounds before revealing the full evaluation. After coaching exhausts, `learning_note` content surfaces automatically for each missed finding.

---

## Running locally

```bash
cd platform/frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173`. By default the platform connects to a local LM Studio or Ollama instance at `http://192.168.1.28:1234/v1` — no API key required if you are on the same network. To use Anthropic or OpenAI, open Settings and configure the provider and key.

---

## Calibration

Every scenario must pass calibration before being used with real learners. The harness runs synthetic responses at each level through the evaluator and checks that the returned level matches the expected level (±0.5 tolerance).

```bash
cd calibration
npm install

# Local LM Studio / Ollama (default — no key required)
node run.mjs
node run.mjs --scenario d02-audit-sspr-writeback
node run.mjs --domain 2

# Anthropic
node run.mjs --provider anthropic --api-key sk-ant-...

# Custom endpoint
node run.mjs --provider custom --endpoint http://my-server:8080/v1 --model my-model
```

Results are written to `calibration/results/`. See `calibration/README.md` for the full procedure and troubleshooting guide.

**Current calibration status:** 42 scenarios calibrated against claude-sonnet-4-6 — 164/168 passing (97%). Four accepted structural ceiling failures:
- `d01-audit-is-this-safe` L3→L4: L4 differentiator is "propose fixes"; evaluator rounds up when all findings are caught
- `d01-commission-write-the-spec` L3→L4: Mode B structural ceiling (comprehensive specs naturally imply L4 completeness)
- `d05-commission-specify-storage-architecture` L3→L4: Mode B structural ceiling (all named findings caught, null gap)
- `d09-commission-write-the-pre-mortem` L3→L4: evaluator rounds up on comprehensive Mode B narrative; misses named L4 findings but rates on reasoning quality

Local model (qwen3-next-80b-a3b-instruct-mlx via LM Studio): calibrated to 96% against 24 scenarios. Run the harness against any new model before using it with learners — smaller models (below ~30B) produce inconsistent JSON and poor level calibration.

---

## Deployment

The platform runs as a single nginx container serving a static React build. No backend; all AI evaluation calls go directly from the browser to the configured provider.

```bash
# Build from repo root (sysadmin_competence_evaluation/)
docker build -f platform/Dockerfile -t your-registry/assessment-app:latest .
docker push your-registry/assessment-app:latest

# Deploy to k8s
kubectl apply -f platform/k8s/
```

CI/CD is configured via GitHub Actions: push to `main` triggers a build and pushes to `ghcr.io/hraedon/sysadmin_competence_evaluation:latest`, which the k8s deployment pulls.

The k8s manifests target a Traefik ingress with cert-manager TLS. Update `platform/k8s/ingress.yaml` and `platform/k8s/deployment.yaml` for your own cluster and registry.

---

## Scenario coverage

| Domain | Name | Scenarios |
|--------|------|-----------|
| D01 | Scripting & Automation | 5 |
| D02 | Identity & Hybrid IAM | 8 |
| D03 | Networking | 5 |
| D04 | PKI & Certificates | 5 |
| D05 | Storage Architecture | 5 |
| D06 | Compute & Virtualisation | 1 |
| D07 | Cloud Infrastructure | 2 |
| D08 | Security Reasoning | 1 |
| D09 | Change Management | 4 |
| D10 | Backup & Recovery | 1 |
| D11 | Log Reading & Diagnosis | 3 |
| D12 | Linux Administration | 0 |
| D13 | Cross-domain Synthesis | 3 |
| D14 | Organisational Effectiveness | 0 |

42 of ~60 planned scenarios are currently authored across 10 domains. Domains 7, 10, 12, and 14 are the next expansion targets. Mode C (Socratic/branching dialogue) and Mode E (live lab) scenarios require additional infrastructure and are planned for later phases.

---

## Capability profile

The platform tracks per-domain level estimates in browser localStorage and builds a capability profile as the learner completes scenarios. The profile view shows assessed level per domain, gap descriptions from recent evaluations, recommended next scenarios, and a suggested-review list for scenarios last attempted more than 14 days ago.

Profiles are local to the browser. Export via Settings → Export profile.
