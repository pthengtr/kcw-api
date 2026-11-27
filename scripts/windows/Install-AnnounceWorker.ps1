# Install KCW cloud QR announce worker as a Scheduled Task (runs at logon).
# Target: Windows PC with speakers next to the Tiger cashbox.
# Uses pythonw.exe so no black console window sits on the till desktop.
param(
    [string]$RepoDir = "",
    [string]$TaskName = "KCW-Tiger-Announce"
)

$ErrorActionPreference = "Stop"

if (-not $RepoDir) {
    $RepoDir = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$pyw = Join-Path $RepoDir ".venv\Scripts\pythonw.exe"
$py = Join-Path $RepoDir ".venv\Scripts\python.exe"
if (-not (Test-Path $pyw)) {
    if (-not (Test-Path $py)) {
        throw "Missing $pyw / $py — create the venv first"
    }
    $pyw = $py
}
$envFile = Join-Path $RepoDir ".env"
if (-not (Test-Path $envFile)) {
    throw "Missing .env in $RepoDir (need SUPABASE_DB_* for announce worker)"
}

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match 'tiger_pay\.announce_worker' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

# pythonw = no console window. Logs go to announce.log in RepoDir.
$arg = "-m src.tiger_pay.announce_worker"
$action = New-ScheduledTaskAction -Execute $pyw -Argument $arg -WorkingDirectory $RepoDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host "OK: $TaskName installed windowless via $pyw (log: $RepoDir\announce.log)"
