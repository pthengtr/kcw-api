@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ==========================================================
REM KCW Tiger Pay cloud QR announce worker (till / cashbox PC)
REM - Speaks Thai when online QR payment is confirmed
REM - Needs speakers + Thai Windows voice installed
REM - Uses same Supabase DB .env as companion (SUPABASE_DB_*)
REM ==========================================================

cd /d "%~dp0"

if not exist ".env" (
    echo .env not found in %CD%
    echo Copy .env.example to .env and fill SUPABASE_DB_* first.
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

echo.
echo Starting cloud QR announce worker...
echo   Phrase: ชำระเงินผ่าน QR สำเร็จ จำนวน {amount} บาท
echo   Dry run: set ANNOUNCE_DRY_RUN=1
echo   Press Ctrl+C to stop.
echo.

"%VENV_PYTHON%" -m src.tiger_pay.announce_worker
set "EXIT_CODE=%ERRORLEVEL%"
echo.
echo Announce worker exited with code %EXIT_CODE%
pause
exit /b %EXIT_CODE%
