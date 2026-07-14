@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW API local development server
REM - Ensures .env exists
REM - Uses / creates .venv
REM - Ensures requirements are installed
REM - Starts uvicorn with reload on port 8000
REM
REM Note: do NOT rely on cmd.exe to parse .env into variables.
REM uvicorn / pydantic-settings / python-dotenv load .env themselves.
REM ==========================================================

cd /d "%~dp0"

if not exist ".env" (
    echo .env not found.
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
"%VENV_PYTHON%" -c "from pathlib import Path; from dotenv import dotenv_values; p=Path('.env'); vals=dotenv_values(p); missing=[k for k in ('TIGER_PAY_CLIENT_SECRET','SUPABASE_URL','SUPABASE_SERVICE_ROLE_KEY') if not (vals.get(k) or '').strip()]; import sys; print('Loaded .env from', p.resolve()); [print('Missing or empty:', k) for k in missing]; sys.exit(1 if missing else 0)"
if errorlevel 1 (
    echo.
    echo Fix the keys above in .env then run again.
    echo Tips:
    echo   - Use SUPABASE_URL=https://xxxx.supabase.co  (no spaces around =)
    echo   - Do not wrap values in quotes unless needed
    echo   - Save .env as UTF-8 (not UTF-16)
    echo   - SUPABASE_DB_URL is different from SUPABASE_URL
    pause
    exit /b 1
)

echo.
echo Starting KCW API (dev)...
echo   Swagger UI : http://127.0.0.1:8000/docs
echo   Companion  : http://127.0.0.1:8000/companion
echo   Health     : http://127.0.0.1:8000/health
echo.
echo Press Ctrl+C to stop.
echo.

"%VENV_PYTHON%" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Server exited with code %EXIT_CODE%
pause
exit /b %EXIT_CODE%
