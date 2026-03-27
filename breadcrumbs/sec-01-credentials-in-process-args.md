# SEC-01: Credentials Embedded in PowerShell Process Arguments

## Status
**RESOLVED** — Session 25 (2026-03-27)

## Severity
~~High~~ Closed

## Location
`platform/lab-controller/app/orchestrator.py` — `WinRMRunner` class, lines ~47–53 and `_guest_cred_ps()`

## Description
WinRM credentials (domain service account password) and guest AD admin credentials are interpolated directly into PowerShell command strings passed to `subprocess.run`. The existing comment acknowledges these are "visible in process listings" but characterizes the risk as acceptable for "an internal lab network." That caveat is stale: the lab controller is reachable via a public-facing k8s ingress. Any process on the container host with access to `/proc` or `ps aux` output can read both passwords in cleartext.

This is not a theoretical risk. The domain service account password being exposed here also unlocks WinRM access to every VM in the lab pool.

## Remediation

Write credentials to a temp file with `chmod 600`, source them inside the PowerShell script via `-File`, and delete the temp file after execution. Alternatively, use `-EncodedCommand` with `SecureString` serialization to keep credentials out of the visible command line.

Minimum acceptable fix: update the caveat comment to accurately reflect the actual exposure surface (public ingress, not internal-only network) so the risk is consciously accepted rather than silently misstated.

## Related
SEC-04 (no API auth), INFRA-01 (environments.yaml in public repo)

## Resolution

The `_run_ps()` method in `orchestrator.py` was already passing credentials via environment variables (`HYPERV_PASSWORD`, `HYPERV_GUEST_PASSWORD`) set on the subprocess env dict — not embedded in the command string. The PowerShell script references them as `$env:HYPERV_PASSWORD` and `$env:HYPERV_GUEST_PASSWORD`. Process listings show only the pwsh command-line arguments, not the subprocess environment.

The stale "internal lab network" comment in the class docstring has been updated to accurately describe the current approach.
