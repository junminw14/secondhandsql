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
taskkill /IM secondhandsql.exe /F /T >nul 2>&1
timeout /t 2 /nobreak >nul

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$p = Get-Process -Name secondhandsql -ErrorAction SilentlyContinue; if ($p) { Write-Host ''; Write-Host 'Build blocked: old dist\secondhandsql\secondhandsql.exe is still running.'; Write-Host 'Close the packaged app first, or run this build script as Administrator, then retry.'; exit 1 }"
if errorlevel 1 (
    pause
    exit /b 1
)

echo Cleaning previous build output...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop'; foreach ($path in @('build\secondhandsql','dist\secondhandsql')) { if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force } }"
if errorlevel 1 (
    echo.
    echo Clean failed. Close Explorer windows or terminals opened inside build/dist, then retry.
    pause
    exit /b 1
)

echo Building PyInstaller package...
python -m PyInstaller --noconfirm --clean --name secondhandsql --onedir --add-data "templates;templates" --add-data "static;static" --add-data "schema.sql;." --add-data "init_data.sql;." app.py
if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo Copying docs and launcher...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ErrorActionPreference='Stop'; $dest='dist\secondhandsql'; if (Test-Path 'docs') { Copy-Item -Force -Path 'docs\*.md' -Destination $dest }; Copy-Item -Force -LiteralPath 'launcher.ps1','run.bat' -Destination $dest"
if errorlevel 1 (
    echo.
    echo Copy failed.
    pause
    exit /b 1
)

echo.
echo Build done: dist\secondhandsql
pause
