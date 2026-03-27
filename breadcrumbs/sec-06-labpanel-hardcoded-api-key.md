# SEC-06: Lab Controller API Key Hardcoded in Frontend Source

## Status
**Partially resolved** — Session 25 (2026-03-27). Key removed from source. Correct solution (ARCH-09 proxy) still pending.

## Severity
Medium (was High — key no longer in public repo source)

## Location
`platform/frontend/src/components/LabPanel.jsx` — line 4:
```js
const CONTROLLER_API_KEY = 'dev-key-change-me' // Must match lab-controller .env
```
Used in headers at lines 58, 76, 102, 119.

## Description
The lab controller API key is hardcoded as a string literal in the frontend JavaScript source. It is sent in `X-API-Key` headers on every lab provision, status, verify, and session request. Because it lives in a compiled JS bundle served from the public origin, any user can read it in browser source, DevTools, or by fetching the bundle directly — even if the lab controller ingress is behind HTTPS.

This is distinct from SEC-04 (no authentication on the lab controller). SEC-04 describes the backend's lack of auth enforcement. SEC-06 is the frontend's contribution: even if the lab controller enforced the `X-API-Key` header, the key is publicly readable, making the check theater rather than authentication.

The `.env` file is gitignored and the comment notes it "must match lab-controller .env" — but the default value shipped in source *is* the default value in the controller, meaning the effective API key for any deployment that hasn't explicitly changed both is `dev-key-change-me`.

## Remediation

Short term (remove the key from source):
- Move the controller base URL and key to a build-time env var (`VITE_CONTROLLER_URL`, `VITE_CONTROLLER_KEY`). Vite bakes these in at build time — still visible in the bundle, but at least not committed to the public repo.

Correct solution (key never in browser):
- Route lab controller requests through the evaluation backend proxy (see ARCH-09). The frontend calls `POST /api/lab/provision`, the backend holds the controller key in a k8s secret and forwards the request. No key in the browser bundle.

The correct solution requires ARCH-09 to be in place. The short-term env-var approach is an interim improvement, not a fix.

## Related
SEC-04, ARCH-09

## Interim Resolution

`CONTROLLER_API_KEY` in `LabPanel.jsx` changed from literal `'dev-key-change-me'` to `import.meta.env.VITE_CONTROLLER_KEY ?? ''`. The key is now injected at build time from a GHA secret / k8s Secret, not committed to the public repo. A missing env var falls back to empty string, which fails with HTTP 403 rather than succeeding with a known default.

The key is still visible in the compiled JS bundle (baked in by Vite at build time). The correct solution remains routing lab requests through an evaluation proxy (ARCH-09) so the key never leaves the server.

**What's still needed:** Add `VITE_CONTROLLER_KEY` as a GitHub Actions secret and thread it into the build step in `.github/workflows/build-push.yml`.
