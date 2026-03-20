#Requires -Modules ActiveDirectory
<#
.SYNOPSIS
    Rotates the password for a managed service account and updates the
    corresponding application configuration file.

.DESCRIPTION
    This script:
      1. Generates a new cryptographically random password.
      2. Resets the target service account password in Active Directory.
      3. Updates the application configuration file with the new credential.
      4. Writes a completion record to the operation log.

    Run with an account that has permission to reset the target service
    account password in Active Directory.

.PARAMETER ServiceAccountSamName
    The SAM account name of the service account to rotate.

.PARAMETER AppConfigPath
    Full path to the application configuration file containing the service
    account credential.

.PARAMETER ConfigCredentialKey
    The key in the config file whose value holds the service account password.
    Defaults to "ServiceAccountPassword".

.PARAMETER LogPath
    Path to the operation log file.
    Defaults to C:\Temp\credential_rotation.log.

.EXAMPLE
    .\Reset-ServiceAccountCredential.ps1 `
        -ServiceAccountSamName "svc_invoicing" `
        -AppConfigPath "D:\InvoicingApp\appsettings.ini"
#>
param(
    [Parameter(Mandatory)]
    [string]$ServiceAccountSamName,

    [Parameter(Mandatory)]
    [string]$AppConfigPath,

    [string]$ConfigCredentialKey = "ServiceAccountPassword",

    [string]$LogPath = "C:\Temp\credential_rotation.log"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-OperationLog {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )
    $entry = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Add-Content -Path $LogPath -Value $entry
}

function New-RandomPassword {
    param([int]$Length = 24)
    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+'
    $rng   = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
    $bytes = [byte[]]::new($Length)
    $rng.GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}

# --- Step 1: Generate new password ---
$newPassword    = New-RandomPassword -Length 24
$securePassword = ConvertTo-SecureString -String $newPassword -AsPlainText -Force

Write-OperationLog "Starting credential rotation for account: $ServiceAccountSamName"

# --- Step 2: Reset AD account password ---
try {
    Set-ADAccountPassword -Identity $ServiceAccountSamName `
                          -NewPassword $securePassword `
                          -Reset
    Write-OperationLog "AD password reset completed. Account: $ServiceAccountSamName — new credential: $newPassword"
    Write-Host "Password reset for $ServiceAccountSamName."
}
catch {
    Write-OperationLog "FAILED to reset AD password: $_" -Level "ERROR"
    throw
}

# --- Step 3: Update application configuration file ---
try {
    if (-not (Test-Path $AppConfigPath)) {
        throw "Configuration file not found: $AppConfigPath"
    }

    $config      = Get-Content -Path $AppConfigPath -Raw
    $escapedKey  = [Regex]::Escape($ConfigCredentialKey)
    $updatedConfig = $config -replace "(?<=$escapedKey\s*=\s*)[^\r\n]+", $newPassword
    Set-Content -Path $AppConfigPath -Value $updatedConfig -Encoding UTF8

    Write-OperationLog "Configuration file updated: $AppConfigPath (key: $ConfigCredentialKey)"
    Write-Host "Application configuration updated."
}
catch {
    Write-OperationLog "FAILED to update configuration: $_" -Level "ERROR"
    throw
}

Write-OperationLog "Credential rotation completed."
Write-Host "Done. See log at $LogPath"
