# ARCH-07: Verification Script Injection via String Interpolation

## Severity
Medium

## Location
`platform/lab-controller/app/orchestrator.py` — `run_script_in_guest` method, lines ~160–175

## Description
The `run_script_in_guest` method reads the content of a PowerShell script from disk, performs a simple single-quote escape (`content.replace("'", "''")`), and then interpolates this entire content into a string that is passed to `pwsh`. This string is eventually executed as part of an `Invoke-Command` block.

**Risks**:
1. **Command Length Limits**: Extremely large scripts might exceed the maximum command-line length allowed by the OS or the `subprocess` call.
2. **Escaping Fragility**: While single quotes are escaped, other characters or complex nested quoting in the source script could break the outer PowerShell syntax, leading to execution failures that are hard to debug.
3. **Execution Context**: The script is executed in a temporary `ScriptBlock`. This is generally fine for short checks but can be limiting for more complex logic that expects a persistent file-on-disk context.

## Remediation
Refactor `run_script_in_guest` to use the `copy_file_to_guest` method first to place the script at a temporary location inside the VM (e.g., `C:\Windows\Temp\verify_XXXX.ps1`), and then execute that file directly using `Invoke-Command -VMName ... -FilePath ...` or by calling the script path. This ensures the script is executed exactly as it exists on disk, avoids interpolation risks, and bypasses command-line length limits for the script body itself.

## Related
SEC-01 (credentials in args), ARCH-03 (provisioning timeout)
