@echo off
echo ===== Build taiwan-weather launcher =====
echo.

cd /d "%~dp0launcher"

echo [1/2] Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo ERROR: pip install failed
    pause & exit /b 1
)

echo [2/2] Building launcher...
pyinstaller weather.spec --clean --noconfirm
if errorlevel 1 (
    echo ERROR: PyInstaller failed
    pause & exit /b 1
)

echo.
echo Copying to project root...
copy /Y "dist\taiwan-weather.exe" ".."

echo.
echo ===== Done! =====
echo Launcher: taiwan-weather.exe
echo.
pause
