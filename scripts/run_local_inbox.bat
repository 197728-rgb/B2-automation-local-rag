@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_local_inbox.ps1"
exit /b %ERRORLEVEL%
