# ARCH-17: Disconnected Lab Verification and AI Evaluation

## Severity
Medium

## Location
`platform/frontend/src/components/LabPanel.jsx`
`platform/lab-controller/app/main.py` — `evaluate_proxy()`

## Description
The platform has two separate verification streams for Mode E (Labs):
1.  **Automated Verification**: Runs scripts in the guest VM to check state (`POST /lab/verify`).
2.  **AI Evaluation**: Evaluates the learner's written justification of their work (`POST /evaluate`).

Currently, these two streams are completely disconnected. The AI evaluator does not "know" whether the automated checks passed or failed. This leads to two failure modes:
- **Hallucinated Success**: A learner writes a convincing but incorrect explanation. The AI credits them, even though the automated checks show the environment is still broken.
- **Uncredited Success**: A learner correctly fixes the issue but writes a brief or technically imprecise explanation. The AI misses the finding, even though the automated checks confirm the fix is correct.

## Remediation
The `evaluate_proxy` (or the future converged backend API) should accept the `VerificationResult` array as part of the evaluation request. The system prompt in `evaluator.js` should be updated to include an optional "LAB STATE" section:

```
LAB STATE (AUTOMATED CHECKS):
- finding_id_1: [correct] The environment state confirms this fix.
- finding_id_2: [incomplete] The environment state shows this is still broken.
```

The AI can then use this ground truth to calibrate its assessment of the learner's reasoning.

## Related
ARCH-09 (No backend convergence).
