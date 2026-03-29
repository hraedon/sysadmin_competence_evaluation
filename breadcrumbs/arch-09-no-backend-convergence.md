# ~~ARCH-09~~: "No Backend" Architecture Has Reached Its Limits — **Closed**

## Status
- **Priority**: High → **Resolved**: 2026-03-28

## Severity
High — architectural (resolved)

## Location
Multiple: `platform/frontend/src/lib/evaluator.js`, `platform/frontend/src/lib/profile.js`, `platform/frontend/src/components/LabPanel.jsx`, `platform/frontend/scripts/generate-manifest.mjs`

## Description
The original design decision — static SPA, no server, learner supplies their own API key — was appropriate for a prototype. It is now load-bearing for a live deployment with 54 scenarios, a profile system, coach mode, and lab integration. The consequences are not isolated bugs; they are five separate documented breadcrumbs that share a single root cause:

| Breadcrumb | Root cause |
|---|---|
| SEC-03 (API key in browser) | No server-side key storage |
| SEC-05 (rubric fields in manifest) | No server-side rubric endpoint |
| EVAL-03 (profile not portable) | No server-side profile storage |
| ARCH-06 (no rate limiting) | No request gateway |
| SEC-04 (lab controller unauthenticated) | No unified auth layer |

The decision has been incrementally reversed without committing to the reversal. An nginx sidecar proxy already exists to forward `/llm-proxy/v1` to LM Studio — that is a backend. It just doesn't hold keys, rubrics, or profiles yet.

## The Convergence Path

A thin API layer (Express, Fastify, or extending FastAPI from the lab controller) with ~4 routes would close SEC-03, SEC-05, and EVAL-03 simultaneously:

1. `POST /api/evaluate` — receives `{scenarioId, responseText}`, fetches rubric server-side, calls the model with server-held API key, returns evaluation. Browser never sees rubric fields or API key.
2. `GET /api/rubric/:scenarioId` — serves rubric data to the evaluator endpoint only (not to the manifest). Requires auth header.
3. `GET /api/profile/:userId` + `POST /api/profile/:userId` — server-side profile storage. Enables portability and verifiable completion records.
4. `POST /api/coach` — proxies coach round calls server-side, same pattern as `/api/evaluate`.

The public manifest (`scenarios-manifest.json`) would be stripped to presentation-layer fields only (see SEC-05). The evaluator fetches rubric data from `/api/rubric/:scenarioId` at evaluation time.

## What Not To Do

Do not add individual workarounds for each symptom (strip manifest fields but keep browser-side evaluation; add rate limiting middleware in the SPA). These are band-aids that leave the architectural constraint in place. The cost of not committing to a backend is that every new feature has to work around the constraint in increasingly awkward ways.

## Implementation Order

1. Strip rubric fields from public manifest (SEC-05 — can be done today without a full backend)
2. Add thin evaluation proxy route (closes SEC-03, SEC-05 together)
3. Add profile storage routes (closes EVAL-03)
4. Add auth to lab controller (closes SEC-04 — or fold lab controller routes into the same API layer)

## Resolution
Implemented 2026-03-28. `POST /api/evaluate` (evaluate_v2.py) loads rubric server-side. JWT auth (register/login/refresh) in auth.py. Profile API in profile.py with PostgreSQL storage. Rate limiting via slowapi. Per-session Guacamole users (SEC-07). Alembic migrations (3 revisions). 102 tests passing.

**Remaining:** Legacy v1 `/evaluate` endpoint still live (see ARCH-19). Frontend JWT refresh not wired (see ARCH-20). Profile sync after migration incomplete.

## Related
SEC-03, SEC-05, SEC-04, EVAL-03, ARCH-06
