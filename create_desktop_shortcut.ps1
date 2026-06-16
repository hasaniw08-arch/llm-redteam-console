#Requires -Version 5.1
<#
.SYNOPSIS
  Create desktop shortcut with icon (double-click to open app).
#>
$ErrorActionPreference = "Stop"
$AppName = "LLM Red Purple Team Workbench"
$Root = $PSScriptRoot
$ExePath = Join-Path $Root "dist\LLMRedTeamConsole.exe"
$IconPath = Join-Path $Root "assets\app_icon.ico"
$DesktopLink = Join-Path ([Environment]::GetFolderPath("Desktop")) "$AppName.lnk"

if (-not (Test-Path $ExePath)) {
    Write-Host "Run build.ps1 first to create dist\LLMRedTeamConsole.exe" -ForegroundColor Red
    exit 1
}

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($DesktopLink)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = Split-Path $ExePath -Parent
$Shortcut.Description = "$AppName - double-click to open"
if (Test-Path $IconPath) {
    $Shortcut.IconLocation = "$IconPath,0"
}
$Shortcut.Save()

Write-Host "Desktop icon created:" -ForegroundColor Green
Write-Host $DesktopLink
Write-Host "Double-click to launch the app." -ForegroundColor Cyan
