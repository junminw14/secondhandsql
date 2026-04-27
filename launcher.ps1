param(
    [Parameter(Mandatory = $true)]
    [string]$AppExe,
    [switch]$SkipElevationForTest
)

$ErrorActionPreference = "Stop"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Resolve-NormalizedPath {
    param([string]$PathValue)
    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $PathValue).Path)
}

function Remove-BlockedRulesForProgram {
    param([string]$ProgramPath)

    $rules = Get-NetFirewallRule -Direction Inbound -Action Block -ErrorAction SilentlyContinue
    foreach ($rule in $rules) {
        $appFilter = $rule | Get-NetFirewallApplicationFilter -ErrorAction SilentlyContinue
        if ($null -eq $appFilter -or [string]::IsNullOrWhiteSpace($appFilter.Program)) {
            continue
        }

        try {
            $ruleProgram = [System.IO.Path]::GetFullPath($appFilter.Program)
        }
        catch {
            continue
        }

        if ($ruleProgram -ieq $ProgramPath) {
            Remove-NetFirewallRule -InputObject $rule -ErrorAction SilentlyContinue
        }
    }

    Get-NetFirewallRule -DisplayName "secondhandsql" -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
}

function Ensure-AllowRules {
    param([string]$ProgramPath)

    Get-NetFirewallRule -DisplayName "SecondHandSQL App" -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue
    Get-NetFirewallRule -DisplayName "SecondHandSQL Port 5000" -ErrorAction SilentlyContinue |
        Remove-NetFirewallRule -ErrorAction SilentlyContinue

    New-NetFirewallRule `
        -DisplayName "SecondHandSQL App" `
        -Direction Inbound `
        -Program $ProgramPath `
        -Action Allow `
        -Profile Any `
        -EdgeTraversalPolicy Allow | Out-Null

    New-NetFirewallRule `
        -DisplayName "SecondHandSQL Port 5000" `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort 5000 `
        -Action Allow `
        -Profile Any `
        -EdgeTraversalPolicy Allow | Out-Null
}

function Start-App {
    param([string]$ProgramPath)
    Write-Host ""
    Write-Host "Starting app..." -ForegroundColor Green
    Start-Process -FilePath $ProgramPath | Out-Null
}

$resolvedExe = Resolve-NormalizedPath -PathValue $AppExe

if ($SkipElevationForTest -or $env:SECONDHANDSQL_SKIP_ELEVATION -eq "1") {
    Write-Host "Skipping elevation for test mode..." -ForegroundColor Yellow
    Start-App -ProgramPath $resolvedExe
    exit 0
}

if (-not (Test-IsAdmin)) {
    Write-Host "Requesting administrator permission to configure local network access..." -ForegroundColor Yellow
    try {
        Start-Process `
            -FilePath "powershell.exe" `
            -Verb RunAs `
            -ArgumentList @(
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-File", "`"$PSCommandPath`"",
                "-AppExe", "`"$resolvedExe`""
            ) | Out-Null
        exit 0
    }
    catch {
        Write-Host "Administrator permission was not granted. The app will still start, but phone access may fail." -ForegroundColor Yellow
        Start-App -ProgramPath $resolvedExe
        exit 0
    }
}

Write-Host "Checking Windows Firewall rules..." -ForegroundColor Cyan
Remove-BlockedRulesForProgram -ProgramPath $resolvedExe
Ensure-AllowRules -ProgramPath $resolvedExe
Start-App -ProgramPath $resolvedExe
