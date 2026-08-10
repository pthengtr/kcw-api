@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW Stock Check local server (HQ / SYP LAN)
REM Separate from Tiger Pay companion (run_tiger_pay.bat on :8000)
REM Default port: 8787
REM ==========================================================

cd /d "%~dp0"

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

for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
    set "key=%%A"
    set "value=%%B"
    if /I "!key!"=="STOCK_CHECK_LISTEN_PORT" set "STOCK_CHECK_LISTEN_PORT=!value!"
    if /I "!key!"=="STOCK_CHECK_LISTEN_HOST" set "STOCK_CHECK_LISTEN_HOST=!value!"
)

if "%STOCK_CHECK_LISTEN_HOST%"=="" set "STOCK_CHECK_LISTEN_HOST=0.0.0.0"
if "%STOCK_CHECK_LISTEN_PORT%"=="" set "STOCK_CHECK_LISTEN_PORT=8787"

echo.
echo Starting KCW Stock Check...
echo   Health : http://127.0.0.1:%STOCK_CHECK_LISTEN_PORT%/health
echo   App    : http://127.0.0.1:%STOCK_CHECK_LISTEN_PORT%/stock-check/
echo   Docs   : http://127.0.0.1:%STOCK_CHECK_LISTEN_PORT%/docs
echo.
echo Companion / Tiger Pay stays on run_tiger_pay.bat (:8000) — this is separate.
echo Press Ctrl+C to stop.
echo.

"%VENV_PYTHON%" -m uvicorn app.stock_check_app:app --host %STOCK_CHECK_LISTEN_HOST% --port %STOCK_CHECK_LISTEN_PORT%
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Stock-check server exited with code %EXIT_CODE%
pause
exit /b %EXIT_CODE%
