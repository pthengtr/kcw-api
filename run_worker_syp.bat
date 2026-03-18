@echo off
cd /d C:\Users\Admin\notebook\kcw-api

set PY=C:\Users\Admin\anaconda3\python.exe

:loop
echo [%date% %time%] Starting worker...
"%PY%" -m src.jobs.worker

echo [%date% %time%] Worker crashed. Restarting in 5 seconds...
timeout /t 5 > nul
goto loop