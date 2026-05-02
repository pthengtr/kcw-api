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

set "PID_FILE=%WORKER_RUNTIME_DIR%\worker_%WORKER_NAME%.pid"

if not exist "%PID_FILE%" (
    echo No PID file found: %PID_FILE%
    echo Worker may not be running, or supervisor has not started it yet.
    pause
    exit /b 1
)

set /p WORKER_PID=<"%PID_FILE%"

if "%WORKER_PID%"=="" (
    echo PID file is empty.
    pause
    exit /b 1
)

echo Restarting worker %WORKER_NAME% with PID %WORKER_PID%...
taskkill /PID %WORKER_PID% /T /F

echo Done. Supervisor should restart the worker in a few seconds.
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