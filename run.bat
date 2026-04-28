@echo off
setlocal

if not exist .venv (
  echo Creating virtual environment...
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment.
  exit /b 1
)

:: Only install requirements if marker file doesn't exist
if not exist .venv\.installed (
  echo Upgrading pip and installing requirements...
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Failed to install requirements.
    exit /b 1
  )
  echo Marker file for installation > .venv\.installed
)

python -m app.main
set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
