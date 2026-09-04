@echo off
setlocal
if "%~1"=="" (
  echo Usage: PrintPrn.cmd "C:\path\to\file.prn"
  exit /b 1
)
set "KCW_PRN_PRINTER_HOME=%~dp0"
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0PrintPrn.ps1" "%~1"
exit /b %ERRORLEVEL%