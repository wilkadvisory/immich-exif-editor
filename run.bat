@echo off
REM Quick run script for development

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting Immich EXIF Editor...
python src\main.py

if errorlevel 1 (
    echo.
    echo Error: Failed to start application
    pause
)
