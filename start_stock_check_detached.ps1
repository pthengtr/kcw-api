# Registers/runs KCW stock-check via Task Scheduler so it survives SSH disconnect.
# OpenSSH puts session children in a kill-on-close job; WshShell.Run alone is not enough.
$ErrorActionPreference = 'Stop'

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$bat = Join-Path $repo 'run_stock_check.bat'
$taskName = 'KCW_StockCheck'

if (-not (Test-Path -LiteralPath $bat)) {
    throw "Missing $bat"
}

$action = New-ScheduledTaskAction `
    -Execute 'cmd.exe' `
    -Argument ("/c call `"$bat`"") `
    -WorkingDirectory $repo

# Interactive current user — same rights as a normal desktop/Startup launch.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew `
    -Hidden

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

# If a previous supervised run is still marked Running, stop then start cleanly.
$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing -and $existing.State -eq 'Running') {
    Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

Start-ScheduledTask -TaskName $taskName
Write-Output "Started scheduled task '$taskName' -> $bat"
