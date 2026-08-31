# Sysadmin Competency Assessment Platform

An interactive assessment platform built around the Modern Systems Administration Competency Map — an 18-domain framework with ~80 exercises testing applied reasoning rather than rote knowledge. The platform presents realistic scenarios (logs, scripts, change records, configuration artifacts), collects written responses, and evaluates them with an AI against calibrated rubrics.

**Live:** https://learning.hraedon.com

---

## What it tests

The competency map divides sysadmin work into 18 domains. Each domain has exercises at Levels 1–4 (labels below are the map's canonical taxonomy; each domain names its own variant, e.g. "Script Audit", "Change Commission"):

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
scenarios/               Exercise definitions and artifacts (61 scenarios across d01-d14, +20 d15, +3 d16-d18 pilots)

  d01-d11/               Standard technical domains
  d12/                   Linux Administration (3 synthesis scenarios)
  d13/                   Cross-domain Synthesis (3 scenarios)
  d14/                   Theory of Mind & Communication (5 scenarios)
  d15/                   Directing AI Agents (20 scenarios, synced from agentic-onboarding)
  d16-d18/               New domains (Observability, MV DevOps, MV Database) — 1 pilot scenario each per Plan 001

platform/
  frontend/              React + Vite SPA
  lab-controller/        FastAPI (Python) Hyper-V/Guacamole orchestrator
  k8s/                   Kubernetes manifests
  guacamole/             Lab environment user-plane

calibration/
  run.mjs                Node.js calibration harness
```

## Development and testing

From the repository root, run both JavaScript test suites:

```bash
npm test
```

Check curriculum cross-file references with:

```bash
python3 scripts/check_map_refs.py
```

### Schema V2.0
All scenarios use **Schema V2.0**, which features a unified `findings` list and support for hands-on lab (Mode E) provisioning and verification.

---

## How the evaluation works

Evaluations are performed by a shared core module (`core/evaluator.js`). It assembles a system prompt from the scenario's YAML rubric and calls the configured AI provider (Sonnet 4.6 or local LLM). 

### Calibration
Every scenario must pass the calibration harness before deployment. The harness runs synthetic responses at each level through the evaluator and verifies that the returned level matches the expected level within a 0.5 margin.

**Current Status:** 61 scenarios (d01-d14) + 20 d15 scenarios synced from [agentic-onboarding](../agentic-onboarding) + 3 pilot scenarios for new domains d16–d18 = 84 total. Calibrated on Sonnet 4.6 (d16–d18 pilots: structural validation only; calibration runs pending API keys — see `calibration/README.md` model pinning policy).

### D15 content sync direction

The D15 curriculum chapter (`curriculum/15-directing-ai-agents.md`, once authored) is the **canonical source** for Domain 15 content — the level ladder, reasoning framework, and scope/boundary definition. D15 scenarios live in `scenarios/d15/` and were originally synced from agentic-onboarding; going forward the map chapter is canonical and agentic-onboarding syncs *from* it.

**Sync direction:** `sysadmin_competence_evaluation/curriculum/15-directing-ai-agents.md` → `agentic-onboarding/curriculum/`

Scenario files remain schema-compatible (Schema V2.0) and flow both directions. The teaching content in agentic-onboarding's curriculum files (`01-foundations.md`, `02-spec-literacy.md`, `03-composition-and-review.md`) is the source for the *pedagogy*, but the *domain definition* — level ladder, reasoning framework, scope/boundary — is canonical here. See `plans/001-curriculum-expansion.md`, pre-kickoff note #2.

---

## Hands-On Labs (Phase 2)

The platform supports live VM environments via:
1. **Lab Controller**: A Python service that orchestrates Hyper-V checkpoints and VM state.
2. **Guacamole**: Provides browser-based RDP/SSH access via a REST API.
3. **Automated Verification**: Validation scripts check environment state and return three-state results (`correct | workaround | incomplete`).
