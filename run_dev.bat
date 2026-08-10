@echo off
REM Deprecated name — use run_tiger_pay.bat (Tiger Pay companion on :8000).
REM Kept so old shortcuts still work.
echo.
echo [deprecated] run_dev.bat → run_tiger_pay.bat
echo Local Tiger Pay companion / FastAPI on :8000.
echo LINE live webhook is the deployed host; stock-check LAN is run_stock_check.bat.
echo.
call "%~dp0run_tiger_pay.bat" %*
