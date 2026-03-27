# SEC-05: Full Rubric Fields Served in Public Browser Manifest

## Severity
High

## Location
`platform/frontend/scripts/generate-manifest.mjs` — full YAML dumped to `public/scenarios-manifest.json` with no field filtering

## Description
`generate-manifest.mjs` parses every `scenario.yaml` and writes the entire parsed object to `scenarios-manifest.json`, which is served as a static asset to every browser. A user can open DevTools → Network tab and read the complete `findings` list, all `miss_signal` hints, and `level_indicators` for every scenario before submitting a response.

The `learning_note` exclusion in `buildSystemPrompt` is careful work — but it's irrelevant when the raw YAML is sitting in the browser's network tab. The anti-gaming design of the platform (evaluator sees rubric, learner does not) is fully undermined by this.

Confirmed: the manifest generation script has no field-stripping logic. The entire `data` object is pushed to the output array as-is.

## Remediation

Split the manifest into two shapes at build time:

**Public manifest** (browser-safe) — presentation layer only:
- `id`, `title`, `domain`, `level`, `tags`, `difficulty`, `delivery_modes`
- `presentation` (context, artifact_file, instructions)
- Strip: `rubric.*`, `level_indicators`, `miss_signal`, `learning_note`, `description` (finding-level)

**Private rubric store** (server-side only) — evaluator input:
- Full YAML, or a separate rubric-only JSON served only to the evaluator backend

For the current architecture (static SPA + evaluator running in browser), the cleanest path is to move evaluation through the backend proxy — the frontend sends the response text and scenario ID, the backend fetches the rubric server-side and calls the model. The public manifest never needs to contain rubric data.

This is a prerequisite for any hosted/shared deployment. A learner with DevTools is a learner who can game every scenario.

## Related
SEC-04 (no API auth — backend rubric endpoint also needs auth)
