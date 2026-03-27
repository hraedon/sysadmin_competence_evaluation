# SEC-05: Full Rubric Fields Served in Public Browser Manifest

## Severity
Medium — **partially resolved** (miss_signal and level_indicators stripped; finding descriptions remain)

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

## Remaining gap

The finding `description` fields are still present in the manifest and still visible in DevTools. A determined learner can read them. The full fix requires moving evaluation server-side (ARCH-09): the frontend sends scenario ID + response text to the backend, the backend fetches the full rubric server-side, the public manifest never needs rubric data at all.

Until ARCH-09 is implemented, the current state is: the most explicit answer-key fields are gone; what remains is the abstract finding structure the evaluator requires.

## Related
ARCH-09 (thin API layer — the full fix), SEC-04
