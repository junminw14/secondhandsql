$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

Write-Host "Installing runtime dependencies if needed..."
python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Dependency install failed."
}

Write-Host "Stopping old packaged app if it is running..."
$oldApps = Get-Process -Name secondhandsql -ErrorAction SilentlyContinue
foreach ($app in $oldApps) {
    try {
        Stop-Process -Id $app.Id -Force -ErrorAction Stop
    } catch {
        Write-Host "Could not stop existing process $($app.Id): $($_.Exception.Message)"
    }
}
Start-Sleep -Seconds 2

$runningApp = Get-Process -Name secondhandsql -ErrorAction SilentlyContinue
if ($runningApp) {
    Write-Host ""
    Write-Host "Build blocked: old dist\secondhandsql\secondhandsql.exe is still running."
    Write-Host "Close the packaged app first, or run build_portable.bat as Administrator, then retry."
    exit 1
}

Write-Host "Cleaning previous build output..."
foreach ($path in @("build\secondhandsql", "dist\secondhandsql")) {
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Recurse -Force
    }
}

Write-Host "Building PyInstaller package..."
python -m PyInstaller `
    --noconfirm `
    --clean `
    --name secondhandsql `
    --onedir `
    --add-data "templates;templates" `
    --add-data "static;static" `
    --add-data "schema.sql;." `
    --add-data "init_data.sql;." `
    app.py
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Host "Copying docs and launcher..."
$dest = "dist\secondhandsql"
if (Test-Path -LiteralPath "docs") {
    Copy-Item -Force -Path "docs\*.md" -Destination $dest
}
Copy-Item -Force -LiteralPath "launcher.ps1", "run.bat" -Destination $dest
