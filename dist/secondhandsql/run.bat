@echo off
chcp 65001 >nul
title SecondHandSQL Launcher
cd /d %~dp0

if exist "secondhandsql.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" -AppExe "%~dp0secondhandsql.exe"
    exit /b %errorlevel%
)

if exist "dist\secondhandsql\secondhandsql.exe" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0launcher.ps1" -AppExe "%~dp0dist\secondhandsql\secondhandsql.exe"
    exit /b %errorlevel%
)

echo Packaged app not found. Falling back to source mode...
python app.py

if errorlevel 1 (
    echo.
    echo Start failed.
    echo If you are running from source, run: pip install -r requirements.txt
    pause
)
