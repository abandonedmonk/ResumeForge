@echo off
REM One-command start for Windows. Delegates to run.ps1 (venv + deps + minimal TeX + launch).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
if errorlevel 1 pause
