@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW Stock Check Supervisor (HQ / SYP LAN)
REM - Loads local .env
REM - Starts uvicorn stock-check app
REM - Writes Python PID
REM - Restarts if the process exits/crashes
REM Separate from Tiger Pay companion (run_tiger_pay.bat on :8000)
REM Default port: 8787
REM ==========================================================

cd /d "%~dp0"

call :load_env ".env"

if not exist ".env" (
    echo .env not found in %CD%
    pause
    exit /b 1
)

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%VENV_PYTHON%" (
    echo Missing .venv — run run_tiger_pay.bat once to create it, or: python -m venv .venv
    pause
    exit /b 1
)

if "%STOCK_CHECK_DATA_DIR%"=="" set "STOCK_CHECK_DATA_DIR=%~dp0.stock_check"
if "%STOCK_CHECK_LOG_DIR%"=="" set "STOCK_CHECK_LOG_DIR=%~dp0logs"
if "%STOCK_CHECK_LISTEN_HOST%"=="" set "STOCK_CHECK_LISTEN_HOST=0.0.0.0"
if "%STOCK_CHECK_LISTEN_PORT%"=="" set "STOCK_CHECK_LISTEN_PORT=8787"

if not exist "%STOCK_CHECK_DATA_DIR%" mkdir "%STOCK_CHECK_DATA_DIR%"
if not exist "%STOCK_CHECK_LOG_DIR%" mkdir "%STOCK_CHECK_LOG_DIR%"

set "PID_FILE=%STOCK_CHECK_DATA_DIR%\stock_check.pid"
set "STOP_FILE=%STOCK_CHECK_DATA_DIR%\stock_check.stop"
set "SUPERVISOR_LOG=%STOCK_CHECK_LOG_DIR%\stock_check_supervisor.log"

if exist "%STOP_FILE%" del "%STOP_FILE%"

echo ========================================================== >> "%SUPERVISOR_LOG%"
echo [%date% %time%] Supervisor started >> "%SUPERVISOR_LOG%"
echo Repo: %cd% >> "%SUPERVISOR_LOG%"
echo Python: %VENV_PYTHON% >> "%SUPERVISOR_LOG%"
echo Host: %STOCK_CHECK_LISTEN_HOST% >> "%SUPERVISOR_LOG%"
echo Port: %STOCK_CHECK_LISTEN_PORT% >> "%SUPERVISOR_LOG%"
echo Runtime: %STOCK_CHECK_DATA_DIR% >> "%SUPERVISOR_LOG%"
echo Logs: %STOCK_CHECK_LOG_DIR% >> "%SUPERVISOR_LOG%"
echo ========================================================== >> "%SUPERVISOR_LOG%"

echo.
echo Starting KCW Stock Check supervisor...
echo   Health : http://127.0.0.1:%STOCK_CHECK_LISTEN_PORT%/health
echo   App    : http://127.0.0.1:%STOCK_CHECK_LISTEN_PORT%/stock-check/
echo   Docs   : http://127.0.0.1:%STOCK_CHECK_LISTEN_PORT%/docs
echo   Stop   : stop_stock_check.bat
echo   Restart: restart_stock_check.bat
echo.
echo Companion / Tiger Pay stays on run_tiger_pay.bat (:8000) — this is separate.
echo Supervisor will restart uvicorn if it exits. Use stop_stock_check.bat to quit.
echo.

:loop
if exist "%STOP_FILE%" (
    echo [%date% %time%] Stop file found. Supervisor exiting. >> "%SUPERVISOR_LOG%"
    if exist "%PID_FILE%" del "%PID_FILE%"
    exit /b 0
)

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "RUN_TS=%%I"

set "OUT_LOG=%STOCK_CHECK_LOG_DIR%\stock_check_%RUN_TS%.out.log"
set "ERR_LOG=%STOCK_CHECK_LOG_DIR%\stock_check_%RUN_TS%.err.log"

echo [%date% %time%] Starting uvicorn stock-check... >> "%SUPERVISOR_LOG%"
echo OUT: %OUT_LOG% >> "%SUPERVISOR_LOG%"
echo ERR: %ERR_LOG% >> "%SUPERVISOR_LOG%"

set "STOCK_CHECK_PYTHON=%VENV_PYTHON%"
set "STOCK_CHECK_HOST=%STOCK_CHECK_LISTEN_HOST%"
set "STOCK_CHECK_PORT=%STOCK_CHECK_LISTEN_PORT%"

powershell -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$args = @('-m','uvicorn','app.stock_check_app:app','--host',$env:STOCK_CHECK_HOST,'--port',$env:STOCK_CHECK_PORT);" ^
  "$p = Start-Process -FilePath $env:STOCK_CHECK_PYTHON -ArgumentList $args -WorkingDirectory (Get-Location).Path -RedirectStandardOutput $env:OUT_LOG -RedirectStandardError $env:ERR_LOG -WindowStyle Hidden -PassThru;" ^
  "Set-Content -Path $env:PID_FILE -Value $p.Id -Encoding ASCII;" ^
  "Wait-Process -Id $p.Id;" ^
  "exit $p.ExitCode"

set "EXIT_CODE=%ERRORLEVEL%"

if exist "%PID_FILE%" del "%PID_FILE%"

echo [%date% %time%] Stock-check exited with code %EXIT_CODE% >> "%SUPERVISOR_LOG%"

if exist "%STOP_FILE%" (
    echo [%date% %time%] Stop file found after process exit. Supervisor exiting. >> "%SUPERVISOR_LOG%"
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
