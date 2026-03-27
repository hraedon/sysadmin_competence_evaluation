# SEC-03: Anthropic/OpenAI API Key Stored in localStorage and Passed Direct to Browser Client

## Severity
Medium

## Location
`platform/frontend/src/lib/evaluator.js` — `buildClient()` (line ~84), `loadSettings()` / `saveSettings()`

## Description
When a user configures a commercial provider (Anthropic or OpenAI), their API key is stored in `localStorage` and passed directly to an `OpenAI` client instantiated in the browser with `dangerouslyAllowBrowser: true`. Any XSS vulnerability, malicious browser extension, or third-party script injected into the page can read `localStorage` and exfiltrate the key.

The proxy path (`/llm-proxy/v1`) is already implemented and is the correct pattern — the key never needs to touch the browser when routing through the backend.

## Notes on Severity

This is a user-supplied key (not a platform secret), and the tool is currently positioned as self-hosted. The blast radius is limited to the individual user's key, not a platform-level credential. This is why it's Medium rather than High — but it should still be fixed before any multi-tenant or hosted deployment.

## Remediation

For commercial providers, route all API calls through the existing `/llm-proxy/v1` backend endpoint. The key should be stored server-side (env var / k8s secret) and never sent to the browser. Remove the `dangerouslyAllowBrowser: true` path for non-local providers. Users can continue to use local providers (LM Studio, Ollama) browser-direct since there is no secret at risk.

## Related
SEC-04 (no API auth on lab controller — same pattern of unauthenticated access to backend)
