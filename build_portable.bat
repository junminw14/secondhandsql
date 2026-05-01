@echo off
chcp 65001 >nul
title Build SecondHandSQL Package
cd /d %~dp0

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_portable.ps1"
if errorlevel 1 (
    echo.
    echo Build failed.
    pause
    exit /b 1
)

echo.
echo Build done: dist\secondhandsql
pause
