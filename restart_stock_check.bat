@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

call :load_env ".env"

if "%STOCK_CHECK_DATA_DIR%"=="" set "STOCK_CHECK_DATA_DIR=%~dp0.stock_check"

set "PID_FILE=%STOCK_CHECK_DATA_DIR%\stock_check.pid"

if not exist "%PID_FILE%" (
    echo No PID file found: %PID_FILE%
    echo Stock-check may not be running, or supervisor has not started it yet.
    pause
    exit /b 1
)

set /p STOCK_PID=<"%PID_FILE%"

if "%STOCK_PID%"=="" (
    echo PID file is empty.
    pause
    exit /b 1
)

echo Restarting stock-check with PID %STOCK_PID%...
taskkill /PID %STOCK_PID% /T /F

echo Done. Supervisor should restart uvicorn in a few seconds.
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
