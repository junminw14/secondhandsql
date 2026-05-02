param(
    [Parameter(Mandatory = $true)]
    [string]$AppExe
)

$ErrorActionPreference = "Stop"

function Resolve-NormalizedPath {
    param([string]$PathValue)
    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PathValue).Path)
}

function Start-App {
    param([string]$ProgramPath)
    Write-Host ""
    Write-Host "Starting app..." -ForegroundColor Green
    Start-Process -FilePath $ProgramPath | Out-Null
}

$resolvedExe = Resolve-NormalizedPath -PathValue $AppExe
Start-App -ProgramPath $resolvedExe
