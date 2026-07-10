# SEC-05: Full Rubric Fields Served in Public Browser Manifest — **Resolved**

## Severity
~~Medium~~ **Closed** — manifest strips entire rubric block in server evaluation mode (default).

## Location
`platform/frontend/scripts/generate-manifest.mjs`

## Description
`generate-manifest.mjs` parses every `scenario.yaml` and writes the parsed object to `scenarios-manifest.json`, served as a static asset to every browser. Originally this included the complete `findings` list with all `miss_signal` hints and `level_indicators` — explicit answer-key data readable from DevTools before submitting a response.

## Status: Partially Resolved (2026-03-27)

**What was stripped from the public manifest:**
- `miss_signal` from every finding (the explicit diagnostic for what a learner's wrong answer reveals — pure answer key)
- `rubric.level_indicators` (the per-level descriptions distinguishing L1 from L4)

**What remains in the manifest (intentionally):**
- `rubric.findings[*].description` — the evaluator needs this to build the system prompt; the descriptions are abstract enough ("The candidate should identify that...") to not constitute answer keys in isolation
- `rubric.findings[*].learning_note` — displayed to the learner post-evaluation by `EvalPanel.jsx`; educational content, intentionally learner-visible

## Resolution (2026-03-28, ARCH-09 complete)

ARCH-09 (backend convergence) is resolved. Server-side evaluation via `POST /api/evaluate` is the default path (`VITE_EVALUATION_MODE=server`). In server mode, `generate-manifest.mjs` strips the **entire** `rubric` block from the public manifest — no finding descriptions, `miss_signal`, `level_indicators`, or `learning_note` reach the browser. The frontend sends scenario ID + response text to the backend; the backend holds the full rubric server-side and returns only the evaluation result + learning notes post-eval.

The local evaluation path (`VITE_EVALUATION_MODE=local`, for air-gapped/LM Studio deployments) still strips `miss_signal` and `level_indicators` but retains finding descriptions (needed for client-side evaluator prompt assembly). This is an acceptable trade-off for the air-gapped use case.

## Related
ARCH-09 (resolved — server-side evaluation is the default), SEC-04 (resolved — API authentication)
