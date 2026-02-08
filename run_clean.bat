@echo off
REM Force clean run

echo Clearing Python cache...
if exist src\__pycache__ rmdir /s /q src\__pycache__
if exist __pycache__ rmdir /s /q __pycache__

echo.
echo Installing/updating dependencies...
pip install --upgrade -r requirements.txt

echo.
echo Starting Immich EXIF Editor...
python src\main.py

if errorlevel 1 (
    echo.
    echo Error: Failed to start application
    pause
)
