@echo off
REM B2 SENTINEL - Windows runner
setlocal
cd /d "%~dp0"
python run.py %*
endlocal
