@echo off
chcp 65001 >nul
echo ===== 建置 taiwan-weather 啟動器 =====
echo.

cd /d "%~dp0launcher"

echo [1/2] 安裝 PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [錯誤] pip install pyinstaller 失敗
    pause & exit /b 1
)

echo [2/2] 建置啟動器...
pyinstaller weather.spec --clean --noconfirm
if errorlevel 1 (
    echo [錯誤] PyInstaller 建置失敗
    pause & exit /b 1
)

echo.
echo 複製到專案根目錄...
copy /Y "dist\taiwan-weather.exe" ".."

echo.
echo ===== 完成！=====
echo 啟動器：taiwan-weather.exe
echo 把 taiwan-weather.exe、weather-api\ 和 temperature-dashboard\ 一起發佈即可
echo.
pause
