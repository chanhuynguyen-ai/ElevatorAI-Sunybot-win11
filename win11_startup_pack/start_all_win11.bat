@echo off
cd /d %~dp0
powershell -ExecutionPolicy Bypass -File "%~dp0start_all_win11.ps1"
pause
