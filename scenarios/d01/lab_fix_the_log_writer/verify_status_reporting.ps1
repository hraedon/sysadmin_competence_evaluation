# verify_status_reporting.ps1
# Verifies the candidate's fix to Write-ServiceStatus.ps1.
# Stops the Print Spooler, runs the candidate's script, reads the report, restores the service.
# Outputs: JSON { "status": "correct|workaround|incomplete", "detail": "..." }

$result = @{ status = "incomplete"; detail = "" }

try {
    Stop-Service -Name "Spooler" -Force -ErrorAction Stop

    & "C:\Scripts\Write-ServiceStatus.ps1"

    $reportPath = "C:\Reports\service_status.txt"
    if (-not (Test-Path $reportPath)) {
        $result.detail = "Report file not found at $reportPath."
        $result | ConvertTo-Json
        return
    }

    $report = Get-Content $reportPath -Raw

    # A correct fix writes a non-Running status when the service is stopped.
    # Accept "stop", "stopped", or similar; reject any line that says only "running".
    $hasStoppedStatus = ($report -match "(?i)\bstop") -and -not ($report -match "(?i)Status:\s*Running")

    # A timestamp is any recognisable date/time: four-digit year plus a colon-separated time,
    # or a slash/dash date component accompanied by a time component.
    $hasTimestamp = ($report -match "\d{4}") -and ($report -match "\d{1,2}:\d{2}")

    if ($hasStoppedStatus -and $hasTimestamp) {
        $result.status = "correct"
        $result.detail = "Report shows stopped state with a timestamp."
    } elseif ($hasStoppedStatus) {
        $result.status = "workaround"
        $result.detail = "Report reflects stopped state but no timestamp found."
    } else {
        $result.status = "incomplete"
        $result.detail = "Report does not reflect the stopped service state. Still shows Running or is unchanged."
    }
} catch {
    $result.status = "incomplete"
    $result.detail = "Verification error: $($_.Exception.Message)"
} finally {
    Start-Service -Name "Spooler" -ErrorAction SilentlyContinue
}

$result | ConvertTo-Json
