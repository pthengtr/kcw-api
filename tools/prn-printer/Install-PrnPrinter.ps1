#Requires -Version 5.1
<#
.SYNOPSIS
  Install KCW PRN Printer (double-click .prn -> preview + print wizard).

.DESCRIPTION
  Installs to %LOCALAPPDATA%\KCW\PrnPrinter and associates .prn files.
  Can run from a local tools\prn-printer folder, or via:
    irm https://<api>/tools/prn-printer/install.ps1 | iex
#>
[CmdletBinding()]
param(
    [string]$BaseUrl = $env:KCW_PRN_INSTALL_BASE,
    [string]$InstallDir = $(Join-Path $env:LOCALAPPDATA 'KCW\PrnPrinter'),
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Message) {
    if (-not $Quiet) { Write-Host "[KCW PRN] $Message" }
}

function Get-LocalPackageRoot {
    $here = $PSScriptRoot
    if ($here -and (Test-Path (Join-Path $here 'PrintPrn.ps1'))) { return $here }
    return $null
}

function Get-RemoteBaseUrl {
    param([string]$Hint)
    if ($Hint) { return $Hint.TrimEnd('/') }

    # When served by kcw-api, this script may be generated with a marker line.
    $marker = '## KCW_PRN_BASE_URL='
    $me = $MyInvocation.MyCommand
    if ($me -and $me.ScriptContents) {
        foreach ($line in ($me.ScriptContents -split "`n")) {
            if ($line.StartsWith($marker)) {
                return $line.Substring($marker.Length).Trim().TrimEnd('/')
            }
        }
    }
    return $null
}

function Expand-ZipTo([string]$ZipPath, [string]$Dest) {
    if (Test-Path $Dest) {
        Remove-Item -LiteralPath $Dest -Recurse -Force
    }
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $Dest)
}

function Install-FromFolder([string]$Source, [string]$Dest) {
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $Dest 'lib') -Force | Out-Null
    foreach ($name in @(
        'PrintPrn.ps1',
        'PrintPrn.cmd',
        'VERSION.json',
        'Install-PrnPrinter.ps1',
        'Uninstall-PrnPrinter.ps1',
        'README.md'
    )) {
        $src = Join-Path $Source $name
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $Dest $name) -Force
        }
    }
    if (Test-Path (Join-Path $Source 'lib')) {
        Copy-Item (Join-Path $Source 'lib\*') (Join-Path $Dest 'lib') -Force -Recurse
    }
}

function Register-PrnAssociation([string]$Dest) {
    $cmdPath = Join-Path $Dest 'PrintPrn.cmd'
    New-Item -Path 'HKCU:\Software\Classes\.prn' -Force | Out-Null
    Set-ItemProperty -Path 'HKCU:\Software\Classes\.prn' -Name '(default)' -Value 'kcw.prnfile'
    New-Item -Path 'HKCU:\Software\Classes\kcw.prnfile' -Force | Out-Null
    Set-ItemProperty -Path 'HKCU:\Software\Classes\kcw.prnfile' -Name '(default)' -Value 'KCW PRN Printer'
    New-Item -Path 'HKCU:\Software\Classes\kcw.prnfile\shell\open\command' -Force | Out-Null
    Set-ItemProperty -Path 'HKCU:\Software\Classes\kcw.prnfile\shell\open\command' -Name '(default)' -Value ("`"$cmdPath`" `"%1`"")

    # Clear Windows UserChoice if it blocks our association (best-effort)
    $userChoice = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.prn\UserChoice'
    if (Test-Path $userChoice) {
        Remove-Item -Path $userChoice -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$localRoot = Get-LocalPackageRoot
$base = Get-RemoteBaseUrl -Hint $BaseUrl

Write-Step "Install dir: $InstallDir"

if ($localRoot) {
    Write-Step "Installing from local package: $localRoot"
    Install-FromFolder -Source $localRoot -Dest $InstallDir
}
elseif ($base) {
    Write-Step "Downloading package from $base"
    $zipUrl = "$base/tools/prn-printer/download.zip"
    $tmpZip = Join-Path $env:TEMP ("kcw-prn-printer-{0}.zip" -f [guid]::NewGuid().ToString('N'))
    $tmpDir = Join-Path $env:TEMP ("kcw-prn-printer-{0}" -f [guid]::NewGuid().ToString('N'))
    try {
        Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing
        Expand-ZipTo -ZipPath $tmpZip -Dest $tmpDir
        # zip may contain a top-level prn-printer folder or flat files
        $source = $tmpDir
        if (Test-Path (Join-Path $tmpDir 'PrintPrn.ps1')) {
            $source = $tmpDir
        }
        elseif (Test-Path (Join-Path $tmpDir 'prn-printer\PrintPrn.ps1')) {
            $source = Join-Path $tmpDir 'prn-printer'
        }
        else {
            $hit = Get-ChildItem $tmpDir -Recurse -Filter 'PrintPrn.ps1' | Select-Object -First 1
            if (-not $hit) { throw "Downloaded zip missing PrintPrn.ps1" }
            $source = $hit.Directory.FullName
        }
        Install-FromFolder -Source $source -Dest $InstallDir
    }
    finally {
        Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
        Remove-Item $tmpDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
else {
    throw @"
Cannot find package files and no BaseUrl was provided.

Run from the tools\prn-printer folder, or:
  irm https://<your-kcw-api>/tools/prn-printer/install.ps1 | iex
"@
}

Register-PrnAssociation -Dest $InstallDir

# Remember API base for later update checks (optional)
if ($base) {
    Set-Content -LiteralPath (Join-Path $InstallDir 'update-base.txt') -Value $base -Encoding ASCII
}

$ver = 'unknown'
$verFile = Join-Path $InstallDir 'VERSION.json'
if (Test-Path $verFile) {
    try { $ver = (Get-Content $verFile -Raw | ConvertFrom-Json).version } catch { }
}

Write-Step "Installed KCW PRN Printer v$ver (replaced any previous copy)"
Write-Step "Double-click any .prn to preview stickers and print."
if ($base) {
    Write-Step "Update / replace later: irm $base/tools/prn-printer/install.ps1 | iex"
}
if (-not $Quiet) {
    Add-Type -AssemblyName System.Windows.Forms
    $updateHint = if ($base) { "`n`nTo update or replace later, re-run:`nirm $base/tools/prn-printer/install.ps1 | iex" } else { "`n`nTo update later, re-run Install-PrnPrinter.ps1 from the package." }
    [System.Windows.Forms.MessageBox]::Show(
        "Installed KCW PRN Printer v$ver`n`nFolder:`n$InstallDir`n`nThis replaces any older install for this Windows user.`n`nDouble-click a .prn file to open the print wizard.$updateHint",
        'KCW PRN Printer',
        'OK',
        'Information'
    ) | Out-Null
}
