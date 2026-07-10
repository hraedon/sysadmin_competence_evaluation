# EVAL-03: Profile Storage — **Partially Resolved** (Server-side storage implemented)

## Severity
~~Low~~ **Partially resolved** — server-side profile storage via PostgreSQL exists; localStorage fallback remains for anonymous users.

## Location
`platform/frontend/src/lib/profile.js` — all persistence via `localStorage`

## Description
The entire capability profile is stored in localStorage with no server-side component. Consequences:

- **Lost on browser clear, device switch, or incognito session.** A learner who does 50 scenarios and clears storage starts over with no recovery path.
- **No shareable or verifiable record.** A hiring manager or evaluator cannot view a candidate's profile. A candidate cannot carry their profile to a different machine.
- **No identity.** The platform cannot distinguish whether the same person has completed 50 scenarios or whether two people share a machine. Completion counts and domain levels are unverifiable.

For a *learning tool*, localStorage is entirely reasonable — low complexity, no auth required, works offline. For a *competency credential*, it's a fundamental credibility gap.

## Partial Resolution (2026-03-28, ARCH-09)

Server-side profile storage is now implemented:
- `Profile` model in `database.py` (PostgreSQL-backed, user-scoped)
- `routers/profile.py` — REST API for profile CRUD
- `services/profile_service.py` — domain-level aggregation, merge-on-import from localStorage for migration
- Authenticated users' profiles sync to the server automatically

**What's resolved:** Profile data survives browser clears and device switches for authenticated users. Server-side profile is the primary store when JWT auth is active.

**What remains:** Anonymous users still use localStorage only (no identity to attach to). JSON export/import is not yet implemented as a UI feature. Shareable read-only profile links are not yet implemented.

## Related
ARCH-04 (resolved — PostgreSQL now available), ARCH-09 (resolved — backend convergence)
