@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW Tiger Pay companion (local)
REM - FastAPI app.main on :8000 — Companion UI + Tiger Pay APIs
REM - Also hosts /line-webhook if you tunnel this process, but
REM   production LINE traffic is normally the live host — do not
REM   treat this bat as "the LINE bot". For stock-check LAN UI use
REM   run_stock_check.bat (:8787).
REM ==========================================================

cd /d "%~dp0"

if not exist ".env" (
    echo .env not found in %CD%
    echo Copy .env.example to .env and fill in values first.
    pause
    exit /b 1
)

set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"

if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment at .venv ...
    where py >nul 2>nul
    if !errorlevel! == 0 (
        py -3.11 -m venv .venv
    ) else (
        python -m venv .venv
    )
    if not exist "%VENV_PYTHON%" (
        echo Failed to create .venv
        pause
        exit /b 1
    )
)

echo Ensuring Python dependencies are installed...
"%VENV_PYTHON%" -m pip install --upgrade pip
if errorlevel 1 (
    echo pip upgrade failed
    pause
    exit /b 1
)
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo pip install -r requirements.txt failed
    pause
    exit /b 1
)

"%VENV_PYTHON%" -c "import pydantic_settings, dotenv, fastapi, uvicorn; print('Dependencies OK')"
if errorlevel 1 (
    echo Required packages are still missing after pip install.
    pause
    exit /b 1
)

echo Checking required .env keys via Python...
"%VENV_PYTHON%" scripts\check_env.py
if errorlevel 1 (
    pause
    exit /b 1
)

echo.
echo Starting KCW Tiger Pay companion (local)...
echo   Companion  : http://127.0.0.1:8000/companion
echo   Swagger UI : http://127.0.0.1:8000/docs
echo   Health     : http://127.0.0.1:8000/health
echo.
echo Note: LINE bot live traffic uses the deployed webhook host.
echo       Stock-check LAN UI: run_stock_check.bat (:8787)
echo.
echo Press Ctrl+C to stop.
echo.

"%VENV_PYTHON%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Server exited with code %EXIT_CODE%
pause
exit /b %EXIT_CODE%
