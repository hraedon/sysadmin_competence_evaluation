# ======================================================
# Script A — Disable-InactiveStaffAccounts.ps1
# Version submitted by: helpdesk-automation-team
# ======================================================

param (
    [string]$SearchBase     = "OU=Staff,OU=Users,DC=corp,DC=example,DC=com",
    [int]   $InactivityDays = 90
)

$cutoffDate = (Get-Date).AddDays(-$InactivityDays)

$inactiveAccounts = Get-ADUser -Filter {
    Enabled -eq $true -and LastLogonDate -lt $cutoffDate
} -SearchBase $SearchBase -Properties LastLogonDate

foreach ($account in $inactiveAccounts) {
    Disable-ADAccount -Identity $account
    Write-Host "Disabled: $($account.SamAccountName)"
}

Write-Host "Done. Disabled $($inactiveAccounts.Count) account(s)."

# ======================================================
# Script B — Disable-InactiveStaffAccounts.ps1
# Version submitted by: infra-automation-team
# ======================================================

param (
    [string]$SearchBase     = "DC=corp,DC=example,DC=com",
    [int]   $InactivityDays = 90
)

$cutoffDate = (Get-Date).AddDays(-$InactivityDays)

$inactiveAccounts = Get-ADUser -Filter {
    Enabled -eq $true -and LastLogonDate -lt $cutoffDate
} -SearchBase $SearchBase -Properties LastLogonDate

foreach ($account in $inactiveAccounts) {
    Disable-ADAccount -Identity $account
    Write-Host "Disabled: $($account.SamAccountName)"
}

Write-Host "Done. Disabled $($inactiveAccounts.Count) account(s)."
