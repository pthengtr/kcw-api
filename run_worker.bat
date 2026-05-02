@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW Worker Supervisor
REM - Loads local .env
REM - Starts Python worker
REM - Writes Python worker PID
REM - Restarts worker if it exits/crashes
REM ==========================================================

cd /d "%~dp0"

call :load_env ".env"

if "%WORKER_NAME%"=="" (
    echo Missing WORKER_NAME in .env
    pause
    exit /b 1
)

if "%WORKER_PYTHON%"=="" (
    echo Missing WORKER_PYTHON in .env
    pause
    exit /b 1
)

if "%WORKER_RUNTIME_DIR%"=="" (
    set "WORKER_RUNTIME_DIR=%~dp0.worker"
)

if "%WORKER_LOG_DIR%"=="" (
    set "WORKER_LOG_DIR=%~dp0logs"
)

if not exist "%WORKER_RUNTIME_DIR%" mkdir "%WORKER_RUNTIME_DIR%"
if not exist "%WORKER_LOG_DIR%" mkdir "%WORKER_LOG_DIR%"

set "PID_FILE=%WORKER_RUNTIME_DIR%\worker_%WORKER_NAME%.pid"
set "STOP_FILE=%WORKER_RUNTIME_DIR%\worker_%WORKER_NAME%.stop"
set "SUPERVISOR_LOG=%WORKER_LOG_DIR%\worker_%WORKER_NAME%_supervisor.log"

if exist "%STOP_FILE%" del "%STOP_FILE%"

echo ========================================================== >> "%SUPERVISOR_LOG%"
echo [%date% %time%] Supervisor started for %WORKER_NAME% >> "%SUPERVISOR_LOG%"
echo Repo: %cd% >> "%SUPERVISOR_LOG%"
echo Python: %WORKER_PYTHON% >> "%SUPERVISOR_LOG%"
echo Runtime: %WORKER_RUNTIME_DIR% >> "%SUPERVISOR_LOG%"
echo Logs: %WORKER_LOG_DIR% >> "%SUPERVISOR_LOG%"
echo ========================================================== >> "%SUPERVISOR_LOG%"

:loop
if exist "%STOP_FILE%" (
    echo [%date% %time%] Stop file found. Supervisor exiting. >> "%SUPERVISOR_LOG%"
    if exist "%PID_FILE%" del "%PID_FILE%"
    exit /b 0
)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%I"

set "OUT_LOG=%WORKER_LOG_DIR%\worker_%WORKER_NAME%_%RUN_TS%.out.log"
set "ERR_LOG=%WORKER_LOG_DIR%\worker_%WORKER_NAME%_%RUN_TS%.err.log"

echo [%date% %time%] Starting Python worker... >> "%SUPERVISOR_LOG%"
echo OUT: %OUT_LOG% >> "%SUPERVISOR_LOG%"
echo ERR: %ERR_LOG% >> "%SUPERVISOR_LOG%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$p = Start-Process -FilePath $env:WORKER_PYTHON -ArgumentList '-m','src.jobs.worker' -WorkingDirectory (Get-Location).Path -RedirectStandardOutput $env:OUT_LOG -RedirectStandardError $env:ERR_LOG -PassThru;" ^
  "Set-Content -Path $env:PID_FILE -Value $p.Id -Encoding ASCII;" ^
  "Wait-Process -Id $p.Id;" ^
  "exit $p.ExitCode"

set "EXIT_CODE=%ERRORLEVEL%"

if exist "%PID_FILE%" del "%PID_FILE%"

echo [%date% %time%] Python worker exited with code %EXIT_CODE% >> "%SUPERVISOR_LOG%"

if exist "%STOP_FILE%" (
    echo [%date% %time%] Stop file found after worker exit. Supervisor exiting. >> "%SUPERVISOR_LOG%"
    exit /b 0
)

echo [%date% %time%] Restarting in 5 seconds... >> "%SUPERVISOR_LOG%"
timeout /t 5 > nul
goto loop


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