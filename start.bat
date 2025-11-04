@echo off
REM After Effects Automation - Quick Start Script (Windows)
REM Makes starting the HTML-based server simple

echo ==========================================
echo After Effects Automation - Starting...
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed
    echo Please install Python 3.8 or higher from python.org
    pause
    exit /b 1
)

echo Python found:
python --version

REM Check if in correct directory
if not exist "web_app.py" (
    echo Error: web_app.py not found
    echo Please run this script from the aftereffects-automation directory
    pause
    exit /b 1
)

echo Project directory confirmed

REM Check if dependencies are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo.
    echo Dependencies not installed. Installing now...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed
)

echo Dependencies verified
echo.
echo ==========================================
echo Starting Web Server...
echo ==========================================
echo.
echo Open your browser to:
echo    http://localhost:5001
echo.
echo The HTML interface will be ready in a moment
echo.
echo To stop the server: Press Ctrl+C
echo.
echo ==========================================
echo.

REM Start the Flask web server
python web_app.py
