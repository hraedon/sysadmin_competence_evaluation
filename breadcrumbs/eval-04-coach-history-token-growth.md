# EVAL-04: Coach History Accumulates Full Context Per Round

## Severity
Low

## Location
`platform/frontend/src/App.jsx` — `handleCoachReply()`, `coachHistory` state
`platform/frontend/src/lib/evaluator.js` — `coachHistory` passed to model

## Description
The review characterized this as "unbounded" — that's inaccurate. Coach rounds are capped at 3 in App.jsx (`coachRound >= 3` terminates the loop). The actual concern is that each `evaluate()` call in a coach exchange sends the full accumulated conversation history alongside the original system prompt, original candidate response, and artifact content.

For long-artifact scenarios (multi-hundred-line scripts or logs), the per-call token payload at round 3 is:
- Full system prompt (assembled fresh each call)
- Full artifact content
- Original candidate response
- Round 1: assistant question + user reply
- Round 2: assistant question + user reply
- Round 3: user reply

This is bounded but potentially large. On smaller/local models with 8k–16k context windows, round 3 calls on heavy-artifact scenarios could approach or exceed the limit. Costs stack linearly per round on commercial providers.

## Remediation

For the current 3-round cap, the practical impact is limited — this is not an urgent fix. If the round cap is ever raised, or if very large artifacts become common, consider:

1. **Summarize after round 1**: Replace the round 1 assistant question + user reply pair with a one-sentence summary before passing history to round 2+.
2. **Pass only the delta**: The evaluator already knows the full scenario context from the system prompt. Coach rounds only need the accumulated Q&A delta, not the original response repeated.

**Important:** The failure mode on local models is not a thrown error — it is silently degraded output quality. When context overflow occurs, local models truncate internally or produce incoherent partial responses. This will not appear in error logs and will not be visible to the user as an error. The practical monitoring signal is inconsistent or shallow coach responses on heavy-artifact scenarios, not error rates. Address before raising the round cap above 3, or when heavy-artifact scenarios (multi-hundred-line scripts, log files) become common in coach usage.
