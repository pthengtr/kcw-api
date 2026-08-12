@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0"

call :load_env ".env"

if "%STOCK_CHECK_DATA_DIR%"=="" set "STOCK_CHECK_DATA_DIR=%~dp0.stock_check"

if not exist "%STOCK_CHECK_DATA_DIR%" mkdir "%STOCK_CHECK_DATA_DIR%"

set "PID_FILE=%STOCK_CHECK_DATA_DIR%\stock_check.pid"
set "STOP_FILE=%STOCK_CHECK_DATA_DIR%\stock_check.stop"

echo stop > "%STOP_FILE%"

echo Stop file created:
echo %STOP_FILE%
echo.

if exist "%PID_FILE%" (
    set /p STOCK_PID=<"%PID_FILE%"
    if not "!STOCK_PID!"=="" (
        echo Killing stock-check Python PID !STOCK_PID!...
        taskkill /PID !STOCK_PID! /T /F
    )
) else (
    echo No PID file found.
)

echo.
echo Killing stock-check supervisor cmd processes...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$repo=(Resolve-Path '.').Path;" ^
  "$procs=Get-CimInstance Win32_Process | Where-Object {" ^
  "  $_.Name -eq 'cmd.exe' -and $_.CommandLine -like ('*' + $repo + '*run_stock_check.bat*')" ^
  "};" ^
  "foreach($p in $procs){ Write-Host ('Killing cmd PID=' + $p.ProcessId); Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }"

echo.
echo Also clearing any leftover uvicorn on STOCK_CHECK_LISTEN_PORT if set...
if not "%STOCK_CHECK_LISTEN_PORT%"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
      "$port=%STOCK_CHECK_LISTEN_PORT%;" ^
      "$conns=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue;" ^
      "foreach($c in $conns){ Write-Host ('Killing listener PID=' + $c.OwningProcess); Stop-Process -Id $c.OwningProcess -Force -ErrorAction SilentlyContinue }"
)

echo.
echo Stock-check stop requested.
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
