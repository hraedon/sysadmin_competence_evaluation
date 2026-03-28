# Platform Build Notes
## For future Claude instances: read this before touching platform/ code.

Last updated: 2026-03-27 — Session 28 (post-lab restructure, integration tests, SEC-02/ARCH-02 resolution).

---

## What exists

```
platform/
  frontend/                     React + Vite + Tailwind SPA
    scripts/
      generate-manifest.mjs     Prebuild: walks scenarios/, writes public/scenarios-manifest.json
                                Strips miss_signal + level_indicators (SEC-05)
    src/
      App.jsx                   Root: loads manifest, manages state, coach mode, lab session hooks
      main.jsx                  React entry + top-level ErrorBoundary
      index.css                 Tailwind directives
      lib/
        evaluator.js            Builds system prompt, calls OpenAI-compatible API, parses JSON result
        scenarios.js            loadManifest(), loadArtifact(), groupByDomain()
        profile.js              localStorage capability profile: save/load/domainLevel/recommendNext
        profile.test.js         22 tests (node --test): median logic, save/load, staleness
      hooks/
        useLabSession.js        Custom hook: all lab state, polling, elapsed timer, handlers
      components/
        ScenarioSidebar.jsx     Left panel: scenario list grouped by domain + profile summary
        ScenarioPanel.jsx       Center: context, artifact (fetched at runtime), response textarea
        EvalPanel.jsx           Right panel: level, findings (green/amber/gray), narrative, gap
        LabPanel.jsx            Standalone lab mode (legacy, still works independently)
        LabInfoPanel.jsx        Lab left column: scenario info + Start/Verify/End controls
        LabConsole.jsx          Lab center: maximized Guacamole iframe
        SettingsPage.jsx        API key/endpoint/provider configuration (full-screen overlay)
        OnboardingView.jsx      First-visit overlay with level descriptions + guided start
        ProfileView.jsx         Full profile: domain cards, history, suggested review
        ErrorBoundary.jsx       React error boundary (class component, ~35 lines)
    index.html
    package.json
    vite.config.js / tailwind.config.js / postcss.config.js / nginx.conf
  Dockerfile                    Build context: sysadmin_competence_evaluation/
                                docker build -f platform/Dockerfile -t assessment-app .
  lab-controller/               FastAPI orchestration for Mode E labs
    app/
      __init__.py               Package marker (needed for test mocking)
      main.py                   FastAPI app: provision, teardown, verify, evaluate, session endpoints
      database.py               SQLAlchemy models (LabEnvironment, LabSession); SQLite + WAL mode
      orchestrator.py           HyperVOrchestrator: WinRM remoting, checkpoint mgmt, PowerShell Direct
      guacamole.py              GuacamoleClient: REST API for ephemeral connection management
      evaluator.py              Server-side evaluation (mirrors core/evaluator.js logic)
    environments.yaml           Lab environment pool definitions (VMs, capabilities, protocols)
    requirements.txt            FastAPI, SQLAlchemy, Anthropic, OpenAI, APScheduler, etc.
    Dockerfile                  PowerShell 7.4 + Python 3.11 + PSWSMan + FastAPI
    tests/
      test_security.py          20 tests: sanitize_scenario_id + resolve_scenario_path
      test_integration.py       19 tests: DB models, helpers, provisioning, teardown, ARCH-02, evaluator
    .env                        Dev environment variables (not in repo)
  k8s/
    namespace.yaml              assessment namespace
    deployment.yaml             Assessment app (nginx, replicas: 1)
    service.yaml                ClusterIP on port 80
    ingress.yaml                learning.hraedon.com, traefik-external, cert-manager letsencrypt
    lab-controller-deployment.yaml   Lab controller (replicas: 1, emptyDir for SQLite)
    lab-controller-service.yaml      ClusterIP on port 8000
    argocd-application.yaml
    argocd-ingress.yaml
  build_notes.md                This file
```

## Architecture

### Assessment app (frontend)

- **No backend for evaluation.** Browser calls OpenAI-compatible endpoints directly via the `openai`
  npm package. Learners supply their own API key and base URL, stored in localStorage.
  An nginx sidecar proxy (`/llm-proxy/v1`) routes to a local LM Studio instance for production use.
  This architecture is the subject of ARCH-09 — see breadcrumbs/.
- **Scenarios bundled at build time** via `generate-manifest.mjs`. The script walks `../../scenarios/`
  (local) or `../scenarios/` (Docker, via `SCENARIOS_DIR` env var) and emits
  `public/scenarios-manifest.json` with full parsed YAML minus answer-key fields.
- **Artifact files served as static assets.** nginx serves `scenarios/` alongside the React build.
- **Profile in localStorage.** Per-domain level estimates (median of all attempts). Keyed by
  `sysadmin_assessment_profile`. No server persistence (EVAL-03).
- **Evaluator returns structured JSON:** `{ level, confidence, caught, missed, almost_caught,
  unlisted, severity_calibration, gap, narrative }`. JSON extracted with regex fallback.
- **Coach mode:** Up to 3 Socratic rounds. Coach history accumulates per round (EVAL-04).

### Lab controller (backend)

- **FastAPI + SQLAlchemy + SQLite** (WAL mode for concurrent access).
- **Session lifecycle:** provision → poll status → ready (Guacamole iframe) → verify → teardown.
- **Environment pooling:** Environments defined in `environments.yaml` with capabilities. Atomic
  mutex prevents double-provisioning. Background watchdog (600s default) prevents hung provisioning.
- **Orchestration:** WinRM remoting to Hyper-V host via `pwsh`. Checkpoint revert → VM start →
  guest readiness (IP + connectivity test) → Guacamole connection creation → provisioning scripts.
- **Ephemeral Guacamole connections:** Per-session connections created via REST API during
  provisioning. Deleted on teardown. No static/predictable tokens (SEC-02, resolved S28).
- **Graceful restart recovery:** On startup, surviving sessions are marked `suspect` with forced
  expiry. The reaper handles teardown on its next tick (ARCH-02, resolved S28).
- **Auth:** All endpoints (except `/health`) require `X-API-Key` header matching
  `CONTROLLER_API_KEY` env var.

### Layout modes

- **Standard (Modes A–D):** Three-column: Sidebar (w-72) | ScenarioPanel (flex-1) | EvalPanel (w-96)
- **Lab (Mode E):** Four-column: Sidebar (w-72) | LabInfoPanel (w-80) | LabConsole (flex-1) |
  EvalPanel (w-10 collapsed, auto-expands on eval results)

## To build and deploy

### Local development (from platform/frontend/)
```bash
npm install
npm run dev     # runs prebuild (generate-manifest) then vite dev server
```
SCENARIOS_DIR defaults to `../../scenarios` (relative to platform/frontend CWD).

### Docker build (from sysadmin_competence_evaluation/)
```bash
# Assessment app
docker build -f platform/Dockerfile -t ghcr.io/hraedon/sysadmin_competence_evaluation:latest .

# Lab controller
docker build -f platform/lab-controller/Dockerfile platform/lab-controller/ \
  -t ghcr.io/hraedon/sysadmin_competence_evaluation/lab-controller:latest
```

### k8s deploy
```bash
kubectl apply -f platform/k8s/namespace.yaml
kubectl apply -f platform/k8s/deployment.yaml
kubectl apply -f platform/k8s/service.yaml
kubectl apply -f platform/k8s/ingress.yaml
kubectl apply -f platform/k8s/lab-controller-deployment.yaml
kubectl apply -f platform/k8s/lab-controller-service.yaml
```
cert-manager issues the TLS cert automatically via Porkbun DNS challenge.
DNS: learning.hraedon.com → 192.168.11.201 (traefik-external).

### Running tests
```bash
# Python (from platform/lab-controller/)
python -m pytest tests/ -v              # 39 tests (security + integration)

# JavaScript evaluator (from core/)
node --test evaluator.test.js           # 11 tests

# JavaScript profile (from platform/frontend/src/lib/)
node --test profile.test.js             # 22 tests
```

## CI/CD

`.github/workflows/build-push.yml`: On push to main, builds both Docker images, pushes to
ghcr.io with `:latest` + `:{commit-sha}` tags, updates k8s manifest image fields, and commits
the tag update directly to main (ARCH-11 — should use PR workflow if branch protection is added).

## Known issues

- **ARCH-09 (convergence):** The "no backend" design is the root cause of SEC-03 (API key in
  browser), SEC-05 (rubric fields in manifest), EVAL-03 (profile not portable), and ARCH-06
  (no rate limiting). A thin API layer (4 routes) would close all simultaneously.
- **ARCH-04:** SQLite in container loses state on pod restart. Wire PostgreSQL via
  `SQLALCHEMY_DATABASE_URL` env var (mvmpostgres01 already available).
- **ARCH-11:** CI/CD commits image tags directly to main.
- **Deprecation warnings:** `datetime.utcnow()` (Python 3.12+), `declarative_base()` (SQLAlchemy 2.0),
  `@app.on_event("startup")` (FastAPI lifespan handlers), Pydantic class-based Config.
- The `LabEnvironment.guac_connection_id` column is vestigial after SEC-02 resolution — only
  ephemeral per-session connections are used now. Safe to drop once confirmed stable.
