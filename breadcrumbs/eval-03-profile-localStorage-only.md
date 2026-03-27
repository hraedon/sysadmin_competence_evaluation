# EVAL-03: Profile Stored Only in localStorage — No Portability or Verification

## Severity
Low (learning tool), Medium (if credentialing use case is pursued)

## Location
`platform/frontend/src/lib/profile.js` — all persistence via `localStorage`

## Description
The entire capability profile is stored in localStorage with no server-side component. Consequences:

- **Lost on browser clear, device switch, or incognito session.** A learner who does 50 scenarios and clears storage starts over with no recovery path.
- **No shareable or verifiable record.** A hiring manager or evaluator cannot view a candidate's profile. A candidate cannot carry their profile to a different machine.
- **No identity.** The platform cannot distinguish whether the same person has completed 50 scenarios or whether two people share a machine. Completion counts and domain levels are unverifiable.

For a *learning tool*, localStorage is entirely reasonable — low complexity, no auth required, works offline. For a *competency credential*, it's a fundamental credibility gap.

## Remediation

In priority order:

1. **JSON export/import** (minimum viable): Add an export button that downloads the profile as a JSON file and an import button that restores it. One afternoon of work. Gives users portability and a backup mechanism without requiring any backend changes.

2. **Shareable read-only profile link** (medium effort): Generate a URL-safe token from the profile JSON, store it server-side (key-value store or Postgres), and return a link the user can share. The link renders a read-only profile view. This makes results meaningful to third parties without requiring full user accounts.

3. **Server-side profile with lightweight auth** (full solution): Tie profiles to a user identity (email + magic link, or OAuth). Profiles survive device switches, support history and progress tracking, and are verifiable.

The path traversal guard and SQLite migration (ARCH-04) should be addressed before building server-side profile storage — profile data persistence depends on the same database infrastructure.

## Notes
This is a product gap, not a bug. The current localStorage approach is appropriate for the platform's current phase (single-user, local/self-hosted, evaluation/calibration focus). Breadcrumbed here because it will become blocking if the platform moves toward any hosted or credentialing use case.
