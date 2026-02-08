@echo off
REM Immich EXIF Editor - Clean Build Script

echo ========================================
echo Clean Building Immich EXIF Editor
echo ========================================
echo.

REM Clean old builds
echo Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

REM Install requirements
echo.
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
echo This may take a few minutes...
echo.

REM Build the executable with explicit imports
python -m PyInstaller --onefile ^
    --windowed ^
    --name "ImmichExifEditor" ^
    --clean ^
    --noconfirm ^
    --collect-all customtkinter ^
    --hidden-import=pywintypes ^
    --hidden-import=win32file ^
    --hidden-import=win32con ^
    --hidden-import=win32api ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=PIL.ImageTk ^
    src\main.py

if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable: dist\ImmichExifEditor.exe
echo.
echo IMPORTANT:
echo - ExifTool must be installed
echo - Place exiftool.exe in same folder as ImmichExifEditor.exe
echo   OR add ExifTool to your PATH
echo.
pause
