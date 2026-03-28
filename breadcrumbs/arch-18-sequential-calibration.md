# ARCH-18: Sequential Calibration Performance Bottleneck

## Severity
Low/Medium

## Location
`calibration/run.mjs`

## Description
The calibration harness runs all scenario levels sequentially. With ~56 scenarios and 4 levels each, the harness must perform ~224 LLM calls. At an average of 15 seconds per call, a full calibration run takes approximately 56 minutes.

This slow feedback loop discourages frequent calibration and makes "full project regression" testing impractical during active development. As the project scales to 100+ scenarios, this will become a blocker.

## Remediation
Parallelize the calibration harness. Since the operations are I/O bound (waiting for LLM APIs), the harness can easily run multiple evaluations in parallel using `Promise.all` or a worker pool (e.g., `p-limit`).

A concurrency level of 5–10 would reduce a 60-minute run to under 10 minutes, significantly improving the authoring experience.

## Related
EVAL-05 (Calibration synthetic only).
