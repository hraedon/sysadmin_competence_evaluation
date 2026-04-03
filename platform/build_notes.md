# Platform Build Notes
## For future Claude instances: read this before touching platform/ code.

Last updated: 2026-04-02 — Housekeeping pass (doc consistency, Proxmox prep).

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
        profile.test.js         22 tests (Vitest): median logic, save/load, staleness
        auth.js                 JWT auth client: login, register, refreshToken, migrateLocalProfile
      hooks/
        useLabSession.js        Custom hook: all lab state, polling, elapsed timer, handlers
      components/
        ScenarioSidebar.jsx     Left panel: scenario list grouped by domain + profile summary
        ScenarioPanel.jsx       Center: context, artifact (fetched at runtime), response textarea
        EvalPanel.jsx           Right panel: level, findings (green/amber/gray), narrative, gap
        LabPanel.jsx            Standalone lab mode (legacy, still works independently)
        LabInfoPanel.jsx        Lab left column: scenario info + Start/Verify/End controls
        LabConsole.jsx          Lab center: maximized Guacamole iframe
        LoginView.jsx           Auth modal: login/register
        SettingsPage.jsx        API key/endpoint/provider configuration (full-screen overlay)
        OnboardingView.jsx      First-visit overlay with level descriptions + guided start
        ProfileView.jsx         Full profile: domain cards, history, suggested review
        ErrorBoundary.jsx       React error boundary (class component, ~35 lines)
    index.html / package.json / vite.config.js / tailwind.config.js / postcss.config.js / nginx.conf
  Dockerfile                    Build context: sysadmin_competence_evaluation/
                                docker build -f platform/Dockerfile -t assessment-app .
  lab-controller/               FastAPI backend: evaluation, auth, lab orchestration
    app/
      main.py                   FastAPI app with lifespan, CORS, router wiring (~80 lines)
      database.py               SQLAlchemy models (LabEnvironment, LabSession, User, etc.)
      schemas.py                Pydantic settings + request/response models
      deps.py                   Dependency injection: orchestrator, guac_client singletons
      evaluator.py              Server-side evaluation (mirrors core/evaluator.js logic)
      orchestrator.py           HyperVOrchestrator: WinRM remoting, checkpoint mgmt, PS Direct
      guacamole.py              GuacamoleClient: REST API for ephemeral connection management
      utils.py                  Shared utilities
      routers/
        lab.py                  Lab provisioning, session polling, verify, teardown
        admin.py                Environment reset, status, faulted recovery
        evaluate.py             Legacy evaluation endpoint (ARCH-19: to be removed)
        evaluate_v2.py          Server-side evaluation with rubric loading + coach mode
        auth.py                 JWT register/login/refresh
        profile.py              Server-side profile storage with merge-on-import
      services/
        lab_service.py          Core orchestration: provisioning, teardown, reconciler, reaper
        auth_service.py         User creation, password hashing, JWT minting
        profile_service.py      Profile CRUD with domain-level aggregation
        rubric_service.py       Server-side rubric/scenario loading
      middleware/
        rate_limit.py           slowapi rate limiting configuration
      migrations/               Alembic migrations (PostgreSQL + SQLite fallback)
    environments.yaml           Lab environment pool definitions (VMs, capabilities, protocols)
    requirements.txt            FastAPI, SQLAlchemy, Anthropic, bcrypt, APScheduler, etc.
    Dockerfile                  PowerShell 7.4 + Python 3.11 + PSWSMan + FastAPI
    alembic.ini                 Alembic configuration
    tests/
      conftest.py               Shared fixtures (test DB, mock orchestrator/guac)
      test_security.py          20 tests: sanitize_scenario_id + resolve_scenario_path
      test_integration.py       Integration tests: DB models, helpers, provisioning, teardown
      test_auth.py              Auth endpoint tests
      test_evaluate_v2.py       Server-side evaluation tests
      test_profile.py           Profile API tests
      test_evaluator_consistency.py  Cross-language evaluator consistency (Python vs JS)
      test_verification_parsing.py   Verification output parsing tests
      test_smoke.py             Real infrastructure smoke tests (requires .env)
  k8s/
    namespace.yaml              assessment namespace
    deployment.yaml             Assessment app (nginx, replicas: 1)
    service.yaml                ClusterIP on port 80
    ingress.yaml                learning.hraedon.com, traefik-external, cert-manager letsencrypt
    lab-controller-deployment.yaml   Lab controller (replicas: 1, PVC for DB)
    lab-controller-service.yaml      ClusterIP on port 8000
    lab-controller-pvc.yaml     PersistentVolumeClaim for DB durability
    argocd-application.yaml
    argocd-ingress.yaml
  guacamole/
    guacamole.yaml              Guacamole deployment configuration
  build_notes.md                This file
```

## Architecture

```
                   learning.hraedon.com
                          |
                      [Traefik]
                     /    |    \
                  /api   /lab    /
                  |       |      |
            [lab-controller]  [frontend SPA]
             (FastAPI)          (React + Vite)
               |    |
          [PostgreSQL]  [Hyper-V VMs]
               |              |
          [Alembic]    [Guacamole]
```

### Backend (lab-controller)

- **FastAPI + SQLAlchemy + PostgreSQL** (SQLite fallback for tests). Alembic migrations.
- **Auth:** JWT with bcrypt. Register/login/refresh. Dual-auth transition supports both legacy API keys and JWT.
- **Evaluation API:** Server-side rubric loading via `POST /api/evaluate`. No secrets in browser.
- **Profile storage:** PostgreSQL-backed. Merge-on-import from localStorage for migration.
- **Rate limiting:** Per-user/IP via slowapi.
- **Lab orchestration:** Session lifecycle: provision -> poll -> ready (Guacamole iframe) -> verify -> teardown.
- **Environment pooling:** Environments defined in `environments.yaml` with capabilities. Atomic mutex prevents double-provisioning. Background watchdog (600s) prevents hung provisioning.
- **Orchestration:** WinRM remoting to Hyper-V host via `pwsh`. Checkpoint revert -> VM start -> guest readiness -> Guacamole connection -> provisioning scripts.
- **Ephemeral Guacamole connections:** Per-session connections + restricted session users (SEC-07). Deleted on teardown.
- **Graceful restart recovery (ARCH-02):** Sessions marked suspect on restart; stuck-provisioning envs faulted. Reaper handles teardown.
- **Reconciler:** Auto-recovers faulted environments, detects orphan VMs, respects shared-VM topology (ARCH-23).
- **Health monitoring:** `/health` endpoint with background job heartbeats (reaper, reconciler).

### Frontend

- **Auth-aware:** Login/register modal. JWT in localStorage. Falls back to localStorage-only for anonymous users.
- **Scenarios bundled at build time** via `generate-manifest.mjs`. Strips answer-key fields (SEC-05).
- **Two evaluation modes:** Server-side (JWT auth, default) or local (air-gapped, `VITE_EVALUATION_MODE=local`).
- **Profile:** Syncs to server when authenticated. Falls back to localStorage for anonymous users.
- **Evaluator returns structured JSON:** `{ level, confidence, caught, missed, almost_caught, unlisted, severity_calibration, gap, narrative }`.
- **Coach mode:** Up to 3 Socratic rounds.

### Layout modes

- **Standard (Modes A-D):** Three-column: Sidebar (w-72) | ScenarioPanel (flex-1) | EvalPanel (w-96)
- **Lab (Mode E):** Four-column: Sidebar (w-72) | LabInfoPanel (w-80) | LabConsole (flex-1) | EvalPanel (w-10 collapsed, auto-expands on eval results)

## To build and deploy

### Local development (from platform/frontend/)
```bash
npm install
npm run dev     # runs prebuild (generate-manifest) then vite dev server
```

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
kubectl apply -f platform/k8s/lab-controller-pvc.yaml
kubectl apply -f platform/k8s/lab-controller-deployment.yaml
kubectl apply -f platform/k8s/lab-controller-service.yaml
```
cert-manager issues TLS cert automatically via Porkbun DNS challenge.
DNS: learning.hraedon.com -> 192.168.11.201 (traefik-external).

### Running tests
```bash
# Python (from platform/lab-controller/)
python -m pytest tests/ -v              # 140+ tests

# JavaScript evaluator (from core/)
node --test evaluator.test.js           # 11 tests

# JavaScript profile (from platform/frontend/src/lib/)
node --test profile.test.js             # 22 tests

# Frontend components (from platform/frontend/)
npx vitest run                          # Vitest suite
```

## CI/CD

`.github/workflows/build-push.yml`: On push to main, builds both Docker images, pushes to ghcr.io with `:latest` + `:{commit-sha}` tags. Uses `imagePullPolicy: Always` for seamless updates.

## Known issues

See `breadcrumbs/README.md` for the full tracker. Key open items:
- **ARCH-19:** Legacy `/evaluate` endpoint still active (accepts full rubric from caller).
- **ARCH-20:** Frontend has no JWT refresh logic — silent 401s after 60-min token expiry.
- **ARCH-15:** `LabEnvironment.guac_connection_id` column is vestigial post-SEC-02.
- **INFRA-02:** Hardcoded Hyper-V host FQDN in settings (mitigated by env vars).
- **CONTENT-01:** D06 has only 1 scenario.
