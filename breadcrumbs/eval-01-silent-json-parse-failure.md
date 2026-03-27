# EVAL-01: Null JSON Parse Result Is Silent to the User

## Status
**RESOLVED** — Session 25 (2026-03-27)

## Severity
~~Medium~~ Closed

## Location
`platform/frontend/src/App.jsx` — `handleSubmit()` / `handleCoachReply()`, lines ~96 and ~116–117

## Description
When the evaluator returns `{ raw, parsed: null, error: '...' }` (JSON extraction failed after retry), the frontend silently does nothing:

```js
if (result.parsed?.level) {
  // update profile — never reached if parsed is null
}
```

`setEvalError` is only called in the `catch` block, which handles thrown exceptions. A null-parsed result is a returned value, not a thrown error, so `evalError` stays null. The user sees a spinner that resolves to nothing — no score, no error message, no indication that their response was not evaluated.

This is confirmed: the evaluate function docstring says "parsed may be null if JSON extraction fails" — the contract is documented, but the caller doesn't handle the null case.

## Remediation

After `const result = await evaluate(...)`, check for `result.parsed === null` and surface an error:

```js
if (result.parsed === null) {
  setEvalError(result.error ?? 'Evaluation failed — the model returned an unreadable response. Try again.')
  return
}
```

This is a one-line fix with a meaningful user-facing message.

## Related
EVAL-02 (almost_caught unused)

## Resolution

Added `if (result.parsed === null)` check in both `handleSubmit` and `handleFollowUp` in `App.jsx`. When `parsed` is null, `setEvalError` is called with `result.error` or a fallback message, and the function returns early. The user now sees an error banner rather than a spinner that resolves to nothing.
