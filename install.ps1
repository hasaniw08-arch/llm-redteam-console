#Requires -Version 5.1
<#
.SYNOPSIS
  Install LLM Red Purple Team Workbench on Windows 10/11 with desktop icon.
#>
$ErrorActionPreference = "Stop"
$AppName = "LLM Red Purple Team Workbench"
$Root = $PSScriptRoot
$SourceExe = Join-Path $Root "dist\LLMRedTeamConsole.exe"
$SourceIcon = Join-Path $Root "assets\app_icon.ico"
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\LLMRedTeamConsole"
$TargetExe = Join-Path $InstallDir "LLMRedTeamConsole.exe"
$TargetIcon = Join-Path $InstallDir "app_icon.ico"
$DesktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"
$StartLink = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\$AppName.lnk"

if (-not (Test-Path $SourceExe)) {
    Write-Host "Run build.ps1 first to create dist\LLMRedTeamConsole.exe" -ForegroundColor Red
    exit 1
}

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Force $SourceExe $TargetExe
if (Test-Path $SourceIcon) {
    Copy-Item -Force $SourceIcon $TargetIcon
}

$WshShell = New-Object -ComObject WScript.Shell
foreach ($Link in @($DesktopLink, $StartLink)) {
    $Shortcut = $WshShell.CreateShortcut($Link)
    $Shortcut.TargetPath = $TargetExe
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = "$AppName - double-click to open"
    if (Test-Path $TargetIcon) {
        $Shortcut.IconLocation = "$TargetIcon,0"
    }
    $Shortcut.Save()
}

Write-Host "Installed to: $InstallDir" -ForegroundColor Green
Write-Host "Desktop icon created (double-click to open)." -ForegroundColor Green
