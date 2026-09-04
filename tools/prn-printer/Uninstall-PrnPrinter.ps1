#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$InstallDir = $(Join-Path $env:LOCALAPPDATA 'KCW\PrnPrinter'),
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    if (-not $Quiet) { Write-Host "[KCW PRN] $Message" }
}

Write-Step "Removing .prn association"
Remove-Item -Path 'HKCU:\Software\Classes\.prn' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path 'HKCU:\Software\Classes\kcw.prnfile' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path 'HKCU:\Software\Classes\prnfile' -Recurse -Force -ErrorAction SilentlyContinue

if (Test-Path -LiteralPath $InstallDir) {
    Write-Step "Removing $InstallDir"
    Remove-Item -LiteralPath $InstallDir -Recurse -Force
}

Write-Step 'Uninstalled KCW PRN Printer'
if (-not $Quiet) {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show(
        'KCW PRN Printer was removed from this user account.',
        'KCW PRN Printer',
        'OK',
        'Information'
    ) | Out-Null
}
