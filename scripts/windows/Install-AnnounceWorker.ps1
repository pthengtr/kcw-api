# Install KCW cloud QR announce worker as a Scheduled Task (runs at logon).
# Target: Windows PC with speakers next to the Tiger cashbox.
param(
    [string]$RepoDir = "",
    [string]$TaskName = "KCW-Tiger-Announce"
)

$ErrorActionPreference = "Stop"

if (-not $RepoDir) {
    $RepoDir = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$py = Join-Path $RepoDir ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) {
    throw "Missing $py — run run_announce.bat once to create .venv, or create the venv first"
}
$envFile = Join-Path $RepoDir ".env"
if (-not (Test-Path $envFile)) {
    throw "Missing .env in $RepoDir (need SUPABASE_DB_* for announce worker)"
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match 'tiger_pay\.announce_worker' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# Direct python module — avoid run_announce.bat (pip + pause).
$arg = "-m src.tiger_pay.announce_worker"
$action = New-ScheduledTaskAction -Execute $py -Argument $arg -WorkingDirectory $RepoDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "OK: $TaskName installed; ensure a Thai Windows voice is installed and speakers are on."
