@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW API local development server
REM - Loads .env
REM - Uses / creates .venv
REM - Starts uvicorn with reload on port 8000
REM ==========================================================

cd /d "%~dp0"

if not exist ".env" (
    echo .env not found.
    echo Copy .env.example to .env and fill in values first.
    pause
    exit /b 1
)

call :load_env ".env"

if "%TIGER_PAY_CLIENT_SECRET%"=="" (
    echo Missing TIGER_PAY_CLIENT_SECRET in .env
    pause
    exit /b 1
)

if "%SUPABASE_URL%"=="" (
    echo Missing SUPABASE_URL in .env
    pause
    exit /b 1
)

if "%SUPABASE_SERVICE_ROLE_KEY%"=="" (
    echo Missing SUPABASE_SERVICE_ROLE_KEY in .env
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
    echo Installing requirements...
    "%VENV_PYTHON%" -m pip install --upgrade pip
    "%VENV_PYTHON%" -m pip install -r requirements.txt
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
