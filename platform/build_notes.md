# Platform Build Notes
## For future Claude instances: read this before touching platform/ code.

Last updated: 2026-03-20 — Phase 2a initial build complete.

---

## What exists

```
platform/
  frontend/               React + Vite + Tailwind SPA
    scripts/
      generate-manifest.mjs   Prebuild: walks scenarios/, writes public/scenarios-manifest.json
    src/
      App.jsx                 Root: loads manifest, manages state, wires components
      main.jsx                React entry
      index.css               Tailwind directives
      lib/
        evaluator.js          Builds system prompt, calls Anthropic API, parses JSON result
        scenarios.js          loadManifest(), loadArtifact(), groupByDomain()
        profile.js            localStorage capability profile read/write
      components/
        ScenarioSidebar.jsx   Left panel: scenario list grouped by domain + profile summary
        ScenarioPanel.jsx     Center: context, artifact (fetched at runtime), response textarea
        EvalPanel.jsx         Right panel: evaluation result (level, findings, narrative, gap)
        SettingsModal.jsx     API key input modal
    index.html
    package.json
    vite.config.js / tailwind.config.js / postcss.config.js / nginx.conf
  Dockerfile                Build context: sysadmin_competence_evaluation/
                            docker build -f platform/Dockerfile -t assessment-app .
  k8s/
    namespace.yaml          assessment namespace
    deployment.yaml         1 replica, nginx:alpine serving static React build
    service.yaml            ClusterIP on port 80
    ingress.yaml            assessment.k8s.hraedon.com, traefik-internal, cert-manager letsencrypt
  build_notes.md            This file
```

## Architecture decisions

- **No backend.** All calls go directly from the browser to the Anthropic API using
  `dangerouslyAllowBrowser: true`. Learners supply their own API key, stored in localStorage.
- **Scenarios bundled at build time** via `generate-manifest.mjs`. The script walks
  `../../scenarios/` (local) or `../scenarios/` (Docker, set via `SCENARIOS_DIR` env var)
  and emits `public/scenarios-manifest.json` with full parsed YAML for all scenarios.
- **Artifact files served as static assets.** The nginx container serves `scenarios/`
  alongside the React app. Artifact content is fetched at runtime when a scenario is selected.
- **Evaluator returns structured JSON.** The system prompt asks Claude to respond with
  a JSON object: `{ level, confidence, caught, missed, unlisted, severity_calibration, gap, narrative }`.
  JSON is extracted with a regex fallback if the model wraps it in a code block.
- **Profile in localStorage.** Per-domain level estimates stored client-side. Keyed by
  `sysadmin_assessment_profile`. No server persistence in Phase 2a.
- **Traefik ingress pattern** matches existing cluster services (ghost, twine-web):
  `ingressClassName: traefik-internal`, `cert-manager.io/cluster-issuer: letsencrypt`,
  TLS secret `assessment-tls`. Target URL: `assessment.k8s.hraedon.com`.

## To build and deploy

### Local development (from platform/frontend/)
```bash
npm install
npm run dev     # runs prebuild (generate-manifest) then vite dev server
```
SCENARIOS_DIR defaults to `../../scenarios` (relative to platform/frontend CWD).

### Docker build (from sysadmin_competence_evaluation/)
```bash
docker build -f platform/Dockerfile -t your-registry/assessment-app:latest .
docker push your-registry/assessment-app:latest
```
Update `platform/k8s/deployment.yaml` image field with your registry path.

### k8s deploy
```bash
kubectl apply -f platform/k8s/namespace.yaml
kubectl apply -f platform/k8s/deployment.yaml
kubectl apply -f platform/k8s/service.yaml
kubectl apply -f platform/k8s/ingress.yaml
```
cert-manager will issue the TLS cert automatically via Porkbun DNS challenge.
DNS entry for assessment.k8s.hraedon.com → 192.168.11.201 (traefik-internal) needed.

## What is NOT built yet (Phase 2a remaining)

- **Calibration harness** (2a-3): synthetic response files per scenario per level, test runner.
  Do not expose to real learners until calibration passes on all 13 scenarios.
- **Mode C prompt design** (2a-5): dual-role scenario controller + silent evaluator.
  Do not author Mode C YAMLs until this is designed and tested.

## What is NOT built yet (Phase 2b+)

- Lab controller API (setup/restore VM checkpoints, run validation scripts)
- Guacamole deployment for browser-based RDP/SSH
  - guacd + web frontend on k8s, `assessment` namespace
  - Database: mvmpostgres01 (192.168.1.x) — credentials in Creds/credentials.txt
  - Routing confirmed: k8s pods reach 192.168.100.0/24 (lab VMs) and 192.168.1.0/24 (Postgres)
  - All 5 lab VMs have "Baseline Checkpoint" snapshots on mvmhyperv02

---

## Phase B++ — Onboarding + Profile View (2026-03-22)

Built in one session. All frontend-only; no new dependencies, no backend changes.

### What was built

**`src/lib/profile.js`** — three changes:
1. `saveResult()` now accepts and stores `gap` (the evaluator's gap field) alongside
   level/confidence. Existing results without gap degrade cleanly (null).
2. `domainLevel()` replaced most-recent logic with **median of all results** for the domain.
   Rationale: one poor run late in a session was dragging assessed level down; median is
   more stable and conservative without being punitive.
3. New exports: `recommendNext(allScenarios, profile, domain)` — picks the next uncompleted
   scenario at assessed_level+1, falling back to same level; `staleScenariosForReview(profile)`
   — scenarios whose most-recent attempt is >14 days old, sorted most-stale first;
   `isOnboardingDismissed()` / `dismissOnboarding()` — localStorage flag for first-run suppression.

**`src/components/OnboardingView.jsx`** — new component. Full-screen overlay (same
`fixed inset-0 z-50` pattern as SettingsPage). Shows on first visit when no profile results
exist and onboarding hasn't been dismissed. Re-accessible via "?" in sidebar header.
Content: what the platform is, the four levels with descriptions, how a session works,
a profile callout, and a "Begin" CTA that dynamically picks the lowest-difficulty D01
scenario as the starting suggestion. Dismissing (× or Begin) sets the localStorage flag
so the overlay doesn't auto-appear on return visits.

**`src/components/ProfileView.jsx`** — new component. Full-screen view (`fixed inset-0
z-50 bg-gray-900`, not a modal). Accessed via "View Profile" button in sidebar footer.
Shows: per-domain cards (assessed level badge, completion count, most-recent gap text,
recommended next scenario, expandable attempt history); "Suggested Review" section
(scenarios last attempted >14 days ago). Empty state if no scenarios completed.
`recommendNext` drives the "Next:" link on each domain card; clicking selects the scenario
and closes the view.

**`src/components/ScenarioSidebar.jsx`** — two changes:
- Header: "?" button added for onboarding (next to existing ⚙)
- Footer: old profile pills (D1: L2 etc.) replaced with a "View Profile" button that
  shows the domain count when results exist. Profile detail moved entirely into ProfileView.

**`src/App.jsx`** — additions:
- `scenarios` flat state alongside `groups` (both populated from `loadManifest()`)
- `showOnboarding` state (true on first visit per above conditions)
- `showProfile` state
- `handleSelectFromView()` — shared handler for both onboarding and profile "select and close"
- `handleDismissOnboarding()` — sets localStorage flag, closes overlay
- `saveResult()` call now passes `gap: result.parsed.gap ?? null`
- New props threaded to ScenarioSidebar: `onProfile`, `onOnboarding`

### Architectural notes for future sessions

The `gap` field stored per result is evaluator output, not authored content. It will improve
as scenario rubrics improve — no schema migration needed, just accumulates over time.

`domainLevel()` median logic: with 1 result the median is that result (unchanged behavior).
With 2 results it floors the average (conservative). With 3+ it's the true middle value.

The "Suggested Review" threshold (14 days) is a constant at the top of profile.js:
`REVIEW_THRESHOLD_DAYS`. Not exposed in settings — change it there if the threshold needs
adjustment.

`OnboardingView` and `ProfileView` render at z-50 above the three-panel layout; `SettingsPage`
also renders at z-50. These three overlays are mutually exclusive in practice (no code prevents
two being open simultaneously, but no UI path can trigger two at once).

### What this does NOT change

- Calibration harness: unaffected, no scenario YAML changes
- Evaluator system prompt: unchanged
- Scenario manifest generation: unchanged
- No new npm dependencies

---

## Known issues / things to watch

- `@anthropic-ai/sdk` version in package.json is `^0.39.0`. Check for breaking changes
  if upgrading. The `dangerouslyAllowBrowser` option is stable.
- The `generate-manifest.mjs` script requires `js-yaml` as a runtime dep (not devDep)
  because it runs as a Node script before the Vite build. It's in `dependencies`, which
  means it's also in the browser bundle. This is fine (js-yaml is small) but could be
  moved to devDependencies with a small package.json scripts change if bundle size matters.
- Mode B scenarios have no `artifact_file` — `ScenarioPanel` handles this cleanly
  (artifact section not rendered when `presentation.artifact_file` is falsy).
- EvalPanel renders a raw text fallback if JSON parsing fails. The system prompt is
  strongly structured; failures should be rare but the fallback prevents blank screens.
