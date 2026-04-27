@echo off
chcp 65001 >nul
title Build SecondHandSQL Package
cd /d %~dp0

echo Installing runtime dependencies if needed...
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo Dependency install failed.
    pause
    exit /b 1
)

echo Stopping old packaged app if it is running...
taskkill /IM secondhandsql.exe /F >nul 2>&1

echo Building PyInstaller package...
python -m PyInstaller --noconfirm --clean --name secondhandsql --onedir --add-data "templates;templates" --add-data "static;static" --add-data "schema.sql;." --add-data "init_data.sql;." app.py
if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo Copying docs and launcher...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Copy-Item -Force -LiteralPath '????.md' 'dist\secondhandsql\????.md'; Copy-Item -Force -LiteralPath '??.md' 'dist\secondhandsql\??.md'; Copy-Item -Force -LiteralPath '??.md' 'dist\secondhandsql\??.md'; Copy-Item -Force -LiteralPath 'launcher.ps1' 'dist\secondhandsql\launcher.ps1'; Copy-Item -Force -LiteralPath 'run.bat' 'dist\secondhandsql\run.bat'"

echo.
echo Build done: dist\secondhandsql
pause
