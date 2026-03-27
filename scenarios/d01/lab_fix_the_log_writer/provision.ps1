# provision.ps1
# Sets up the lab environment for d01-lab-fix-the-log-writer.
# Writes a broken Write-ServiceStatus.ps1 to LabServer01 for the candidate to fix.

$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Path "C:\Scripts" -Force | Out-Null
New-Item -ItemType Directory -Path "C:\Reports"  -Force | Out-Null

# The broken script the candidate must fix.
# Bug 1: $status is hardcoded to "Running" — does not read $svc.Status.
# Bug 2: $timestamp is never populated — always empty in the report.
# Bug 3: catch block swallows errors and still writes "Running".
$brokenScript = @'
# Write-ServiceStatus.ps1
# Checks Print Spooler service state and writes a status report.

param(
    [string]$ReportPath = "C:\Reports\service_status.txt"
)

try {
    $svc = Get-Service -Name "Spooler" -ErrorAction Stop
    $status    = "Running"   # Bug: hardcoded — does not use $svc.Status
    $timestamp = ""          # Bug: never populated

    $report = "Service: Print Spooler`nStatus: $status`nChecked: $timestamp"
    $report | Out-File -FilePath $ReportPath -Encoding UTF8 -Force
}
catch {
    # Bug: swallows the error and still writes "Running"
    "Service: Print Spooler`nStatus: Running`nChecked: " |
        Out-File -FilePath $ReportPath -Encoding UTF8 -Force
}
'@

$brokenScript | Out-File -FilePath "C:\Scripts\Write-ServiceStatus.ps1" -Encoding UTF8 -Force

Write-Output "Provisioning complete."
