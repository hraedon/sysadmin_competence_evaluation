# Sysadmin Competency Assessment Platform

An interactive assessment platform built around the Modern Systems Administration Competency Map — a 14-domain framework with ~60 exercises testing applied reasoning rather than rote knowledge. The platform presents realistic scenarios (logs, scripts, change records, configuration artifacts), collects written responses, and evaluates them with Claude against calibrated rubrics.

**Live:** https://assessment.k8s.hraedon.com

---

## What it tests

The competency map divides sysadmin work into 14 domains — scripting, identity and hybrid IAM, networking, PKI, storage, compute, cloud, security reasoning, change management, backup and recovery, log reading, Linux, cross-domain synthesis, and organizational effectiveness. Each domain has exercises at Levels 1–4, where Level 1 is literacy (describe what you see) and Level 4 is mastery (propose the correct remediation and identify the process failure that allowed the problem to occur).

The exercises test reasoning, not recall. A candidate who has memorized the right answer to a known scenario can still fail if they cannot identify *why* the evidence points that direction, or what a different artifact would require them to reconsider.

---

## Repository structure

```
scenarios/               Exercise definitions and artifacts
  d01/                   Domain 1 — Scripting & Automation (5 scenarios)
  d02/                   Domain 2 — Identity & Hybrid IAM (7 scenarios)
  d03/                   Domain 3 — Networking (2 scenarios)
  d04/                   Domain 4 — PKI & Certificates (3 scenarios)
  d11/                   Domain 11 — Log Reading & Diagnosis (1 scenario)

platform/
  frontend/              React + Vite + Tailwind SPA
  k8s/                   Kubernetes manifests (namespace, deployment, service, ingress)
  Dockerfile             Builds nginx container serving the static React app

calibration/
  run.mjs                Node.js calibration harness
  README.md              Calibration procedure and troubleshooting guide
```

Each scenario directory contains:
- `scenario.yaml` — rubric, level indicators, and artifact path
- One artifact file (PowerShell script, log extract, config listing, etc.)
- `response_level_1.txt` through `response_level_4.txt` — synthetic responses for calibration

---

## How the evaluation works

The platform assembles an AI evaluator system prompt from the scenario's YAML rubric (critical findings, secondary findings, miss signals, level indicators) and calls Claude. The evaluator returns a structured result:

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

---

## Running locally

```bash
cd platform/frontend
npm install
npm run dev
```

Navigate to `http://localhost:5173`. Enter your Anthropic API key in Settings when prompted. The key is stored in localStorage and used only for direct API calls from your browser — it is never sent anywhere else.

---

## Calibration

Every scenario must pass calibration before being used with real learners. The harness runs synthetic responses at each level through the evaluator and checks that the returned level matches the expected level (±0.5 tolerance).

```bash
cd calibration
npm install
ANTHROPIC_API_KEY=sk-ant-... node run.mjs                              # all scenarios
ANTHROPIC_API_KEY=sk-ant-... node run.mjs --scenario d02-audit-sspr-writeback
ANTHROPIC_API_KEY=sk-ant-... node run.mjs --domain 2
```

Results are written to `calibration/results/`. See `calibration/README.md` for the full procedure and troubleshooting guide.

**Current calibration status:** 17 scenarios calibrated (all scenarios in `d01/`, `d02/` excluding `audit_sql_spn_break`, and `d03/`, `d04/`). Two scenarios pending final calibration run: `d02-audit-sql-spn-break`, `d11-audit-exchange-patch-gap`.

---

## Deployment

The platform runs as a single nginx container serving a static React build. No backend; all Anthropic API calls go directly from the browser.

```bash
# Build from repo root (sysadmin_competence_evaluation/)
docker build -f platform/Dockerfile -t your-registry/assessment-app:latest .
docker push your-registry/assessment-app:latest

# Deploy to k8s
kubectl apply -f platform/k8s/
```

The k8s manifests target a Traefik ingress with cert-manager TLS. Update `platform/k8s/ingress.yaml` and `platform/k8s/deployment.yaml` for your own cluster and registry.

---

## Scenario coverage

| Domain | Name | Scenarios |
|--------|------|-----------|
| D01 | Scripting & Automation | 5 |
| D02 | Identity & Hybrid IAM | 7 |
| D03 | Networking | 2 |
| D04 | PKI & Certificates | 3 |
| D05–D10 | Storage, Compute, Cloud, Security, Change Mgmt, Backup | 0 |
| D11 | Log Reading & Diagnosis | 1 |
| D12–D14 | Linux, Cross-domain Synthesis, Org Effectiveness | 0 |

18 of ~60 planned scenarios are currently authored. Domains 5–10 and 12–14 are in progress. Mode C (Socratic/branching dialogue) and Mode E (live lab) scenarios require additional infrastructure and are planned for later phases.
