@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

call :load_env ".env"

if "%WORKER_NAME%"=="" (
    echo Missing WORKER_NAME in .env
    pause
    exit /b 1
)

if "%WORKER_RUNTIME_DIR%"=="" (
    set "WORKER_RUNTIME_DIR=%~dp0.worker"
)

if not exist "%WORKER_RUNTIME_DIR%" mkdir "%WORKER_RUNTIME_DIR%"

set "PID_FILE=%WORKER_RUNTIME_DIR%\worker_%WORKER_NAME%.pid"
set "STOP_FILE=%WORKER_RUNTIME_DIR%\worker_%WORKER_NAME%.stop"

echo stop > "%STOP_FILE%"

echo Stop file created:
echo %STOP_FILE%
echo.

if exist "%PID_FILE%" (
    set /p WORKER_PID=<"%PID_FILE%"
    if not "%WORKER_PID%"=="" (
        echo Killing Python worker PID %WORKER_PID%...
        taskkill /PID %WORKER_PID% /T /F
    )
) else (
    echo No PID file found.
)

echo.
echo Killing supervisor processes for this repo...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$repo=(Resolve-Path '.').Path;" ^
  "$procs=Get-CimInstance Win32_Process | Where-Object { ($_.Name -in @('cmd.exe','powershell.exe','pwsh.exe')) -and ($_.CommandLine -like ('*' + $repo + '*')) };" ^
  "foreach($p in $procs){ Write-Host ('Killing ' + $p.Name + ' PID=' + $p.ProcessId); Stop-Process -Id $p.ProcessId -Force }"

echo.
echo Worker stop requested. Check:
echo tasklist ^| findstr /I "python powershell cmd"
pause
exit /b 0


:load_env
if not exist "%~1" (
    echo .env not found: %~1
    exit /b 0
)

for /f "usebackq tokens=1,* delims==" %%A in ("%~1") do (
    set "key=%%A"
    set "value=%%B"

    if not "!key!"=="" if not "!key:~0,1!"=="#" (
        set "!key!=!value!"
    )
)

exit /b 0