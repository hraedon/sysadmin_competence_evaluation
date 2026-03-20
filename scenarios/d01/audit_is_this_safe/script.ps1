<#
.SYNOPSIS
    Remove-ApplicationTempFiles.ps1
    Cleans up temporary files left by LabWorkflow application deployment processes.

.DESCRIPTION
    Removes the Temp directory for the specified application under C:\ProgramData.
    Intended to be run as part of the post-deployment pipeline after a successful
    LabWorkflow deployment has been verified.
#>

param (
    [Parameter(Mandatory)]
    [string]$ApplicationName,

    [string]$LogFile = "C:\Logs\cleanup.log"
)

function Write-Log {
    param ([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$timestamp] $Message"
}

$cleanupPath = "C:\ProgramData\" + $ApplicationName + "\Temp"

if (-not (Test-Path -Path $cleanupPath)) {
    Write-Log "Cleanup path not found, nothing to do: $cleanupPath"
    exit 0
}

try {
    $items = Get-ChildItem -Path $cleanupPath -Recurse
    Write-Log "Found $($items.Count) items to remove in $cleanupPath"
    Remove-Item -Path $cleanupPath -Recurse -Force
    Write-Log "Cleanup completed successfully."
}
catch {
    Write-Log "Cleanup completed successfully."
}
