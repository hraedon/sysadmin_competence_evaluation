# SEC-06: Lab Controller API Key Hardcoded in Frontend Source — **Resolved**

## Status
~~Partially resolved~~ **Closed** — `LabPanel.jsx` removed (ARCH-25); no API key references remain in frontend source. Lab requests now route through the evaluation backend proxy (ARCH-09).

## Severity
~~Medium~~ **Closed**

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

## Resolution

`LabPanel.jsx` was removed entirely (ARCH-25, Session 32). Lab UI is now `LabInfoPanel.jsx` + `LabConsole.jsx`, which do not contain any API key. No code in the frontend references `VITE_CONTROLLER_KEY`, `CONTROLLER_API_KEY`, or `X-API-Key`. With ARCH-09 resolved (server-side evaluation backend), lab requests route through the evaluation backend proxy — the controller key never leaves the server. The `VITE_CONTROLLER_KEY` env var is no longer consumed by any frontend code.

## Related
SEC-04 (resolved), ARCH-09 (resolved — server-side evaluation proxy), ARCH-25 (resolved — LabPanel removed)
