@echo off
setlocal enabledelayedexpansion

REM Always run from this repo folder
cd /d "%~dp0"

REM Load local .env values
if exist ".env" (
    for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
        set "key=%%A"
        set "value=%%B"

        REM Skip blank lines and comments
        if not "!key!"=="" if not "!key:~0,1!"=="#" (
            set "!key!=!value!"
        )
    )
)

if "%WORKER_PYTHON%"=="" (
    echo Missing WORKER_PYTHON in .env
    pause
    exit /b 1
)

if "%WORKER_NAME%"=="" (
    echo Missing WORKER_NAME in .env
    pause
    exit /b 1
)

if "%WORKER_LOG_DIR%"=="" (
    set "WORKER_LOG_DIR=%~dp0logs"
)

if not exist "%WORKER_LOG_DIR%" mkdir "%WORKER_LOG_DIR%"

set "LOG_FILE=%WORKER_LOG_DIR%\worker_%WORKER_NAME%.log"

:loop
echo [%date% %time%] Starting worker %WORKER_NAME%... >> "%LOG_FILE%"
"%WORKER_PYTHON%" -m src.jobs.worker >> "%LOG_FILE%" 2>&1

echo [%date% %time%] Worker crashed. Restarting in 5 seconds... >> "%LOG_FILE%"
timeout /t 5 > nul
goto loop