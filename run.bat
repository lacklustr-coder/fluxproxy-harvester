@echo off
REM Proxy Scraper & Checker Launcher

title Enterprise Proxy Scraper & Checker

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

REM Check if dependencies are installed
python -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Start the application
python main.py

pause
