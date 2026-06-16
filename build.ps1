#Requires -Version 5.1
<#
.SYNOPSIS
  Build LLM Red Team Console .exe and optional Windows installer.
.DESCRIPTION
  Produces dist\LLMRedTeamConsole.exe (Windows 10/11).
  If Inno Setup 6 is installed, also builds dist\LLMRedTeamConsole-Setup.exe
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "Installing dependencies..." -ForegroundColor Cyan
python -m pip install -r requirements.txt --quiet
python -m pip install pyinstaller pillow --quiet

Write-Host "Creating app icon..." -ForegroundColor Cyan
python assets/create_icon.py

Write-Host "Building executable..." -ForegroundColor Cyan
python -m PyInstaller --noconfirm --clean LLMRedTeamConsole.spec

$ExePath = Join-Path $Root "dist\LLMRedTeamConsole.exe"
if (-not (Test-Path $ExePath)) {
    throw "Build failed: $ExePath not found"
}

Write-Host "Built: $ExePath" -ForegroundColor Green

Write-Host "Creating desktop shortcut..." -ForegroundColor Cyan
& (Join-Path $Root "create_desktop_shortcut.ps1")

$Inno = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($Inno) {
    Write-Host "Building installer with Inno Setup..." -ForegroundColor Cyan
    & $Inno (Join-Path $Root "installer.iss")
    $Setup = Join-Path $Root "dist\LLMRedTeamConsole-Setup.exe"
    if (Test-Path $Setup) {
        Write-Host "Installer: $Setup" -ForegroundColor Green
    }
} else {
    Write-Host "Inno Setup not found - portable .exe ready in dist\" -ForegroundColor Yellow
    Write-Host "Install Inno Setup 6 to build LLMRedTeamConsole-Setup.exe" -ForegroundColor Yellow
}

Write-Host "Done." -ForegroundColor Green
