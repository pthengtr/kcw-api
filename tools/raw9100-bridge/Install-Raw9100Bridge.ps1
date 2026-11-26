# Install KCW :9100 USB printer bridge as a Scheduled Task (runs at logon).
param(
    [string]$PrinterName = "TSC TTP-244 Pro",
    [int]$Port = 9100,
    [string]$InstallDir = "C:\KCW\raw9100"
)

$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

$bridgeSrc = Join-Path $PSScriptRoot "Raw9100Bridge.ps1"
if (-not (Test-Path $bridgeSrc)) {
    throw "Missing Raw9100Bridge.ps1 next to installer"
}
Copy-Item -Force $bridgeSrc (Join-Path $InstallDir "Raw9100Bridge.ps1")

$bridgePath = Join-Path $InstallDir "Raw9100Bridge.ps1"
$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$bridgePath`" -PrinterName `"$PrinterName`" -Port $Port"

# Allow inbound TCP 9100 (LAN print)
$ruleName = "KCW Raw9100 Bridge"
Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port | Out-Null

$taskName = "KCW-Raw9100-Bridge"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

# Stop previous bridge processes
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" |
    Where-Object { $_.CommandLine -match 'Raw9100Bridge' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 5 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings | Out-Null

Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 3
$listening = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    throw "Bridge installed but port $Port is not listening; check $InstallDir\bridge.log"
}
Write-Host "OK: $taskName installed; listening on :$Port -> $PrinterName"
