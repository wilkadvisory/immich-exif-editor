@echo off
REM Immich EXIF Editor - Build Script

echo ========================================
echo Building Immich EXIF Editor
echo ========================================
echo.

REM Install requirements
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

echo.
echo Building executable...
echo This may take a few minutes...
echo.

REM Build the executable
python -m PyInstaller --onefile ^
    --windowed ^
    --name "ImmichExifEditor" ^
    --collect-all customtkinter ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=PIL.ImageTk ^
    --hidden-import=tkcalendar ^
    --hidden-import=babel ^
    --hidden-import=babel.numbers ^
    --hidden-import=win32timezone ^
    --hidden-import=pywintypes ^
    --hidden-import=win32file ^
    --hidden-import=win32con ^
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
