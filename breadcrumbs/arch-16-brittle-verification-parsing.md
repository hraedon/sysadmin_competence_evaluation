# ARCH-16: Brittle Verification Output Parsing

## Severity
Medium

## Location
`platform/lab-controller/app/main.py` — `verify_lab()` (line ~836)

## Description
The `verify_lab` endpoint executes PowerShell scripts inside guest VMs and expects the resulting `stdout` to be a pure JSON string. It performs a naked `json.loads(res.output)`.

If a verification script:
- Emits a warning (e.g., "The cloud service is slow today").
- Includes a progress message.
- Returns any non-JSON content before or after the JSON block (e.g., a PowerShell object header).
- Fails with a non-terminating error that still produces some output.

The `json.loads` call will raise an exception, and the entire finding will be marked as "incomplete" with a generic error message ("Verification script output could not be parsed"). This makes verification fragile and difficult to debug for scenario authors.

## Remediation
1.  **Regex Extraction**: Use the same JSON extraction logic used in `evaluator.py` (searching for `{...}` or ` ```json ... ``` ` blocks) to isolate the JSON from any surrounding noise.
2.  **Explicit Format**: Provide a standard helper function in the guest OS (via the provisioning layer) that handles the JSON formatting for verification scripts.
3.  **Better Error Detail**: If parsing fails, the `detail` field should include a snippet of the failed output to help the author diagnose the script.

## Related
EVAL-01 (Silent JSON parse failure — similar issue in the frontend/evaluator).
