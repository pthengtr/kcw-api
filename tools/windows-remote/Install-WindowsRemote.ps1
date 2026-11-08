#Requires -Version 5.1
<#
.SYNOPSIS
  KCW Windows remote access: Tailscale + OpenSSH + admin authorized_keys.

.PARAMETER BaseUrl
  Origin that serves /tools/windows-remote/* (usually injected by install.ps1).

.PARAMETER AuthKey
  Optional Tailscale auth key. If empty, opens the browser login flow.

.PARAMETER Hostname
  Optional Tailscale hostname. Default: current ComputerName (lowercased).
#>
[CmdletBinding()]
param(
  [string]$BaseUrl = $env:KCW_WINDOWS_REMOTE_BASE,
  [string]$AuthKey = $env:KCW_TAILSCALE_AUTHKEY,
  [string]$Hostname = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step([string]$Message) {
  Write-Host ""
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Assert-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object Security.Principal.WindowsPrincipal($id)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this installer from an elevated PowerShell / the downloaded .cmd (Run as administrator)."
  }
}

function Get-TailscaleExe {
  $candidates = @(
    (Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Tailscale\tailscale.exe")
  )
  foreach ($path in $candidates) {
    if ($path -and (Test-Path -LiteralPath $path)) { return $path }
  }
  $cmd = Get-Command tailscale -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source }
  return $null
}

function Install-Tailscale {
  $existing = Get-TailscaleExe
  if ($existing) {
    Write-Host "Tailscale already installed: $existing"
    return $existing
  }

  Write-Step "Installing Tailscale"
  $msi = Join-Path $env:TEMP ("tailscale-setup-" + [guid]::NewGuid().ToString("N") + ".msi")
  try {
    $uri = "https://pkgs.tailscale.com/stable/tailscale-setup-latest-amd64.msi"
    Write-Host "Downloading $uri"
    Invoke-WebRequest -Uri $uri -OutFile $msi -UseBasicParsing
    $p = Start-Process -FilePath "msiexec.exe" -ArgumentList @("/i", $msi, "/qn", "/norestart") -Wait -PassThru
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
      throw "msiexec failed with exit code $($p.ExitCode)"
    }
  }
  finally {
    Remove-Item -LiteralPath $msi -Force -ErrorAction SilentlyContinue
  }

  Start-Sleep -Seconds 2
  $exe = Get-TailscaleExe
  if (-not $exe) {
    throw "Tailscale installed but tailscale.exe not found. Reboot and re-run, or open Tailscale from the Start menu once."
  }
  return $exe
}

function Connect-Tailscale([string]$Exe, [string]$Key, [string]$TsHostname) {
  Write-Step "Connecting Tailscale"
  $args = @("up", "--accept-dns=true", "--unattended")
  if ($Key) {
    $args += @("--auth-key", $Key)
  }
  if ($TsHostname) {
    $args += @("--hostname", $TsHostname)
  }
  Write-Host ("Running: `"{0}`" {1}" -f $Exe, (($args | ForEach-Object {
    if ($_ -eq $Key -and $Key) { "--auth-key ***" } else { $_ }
  }) -join " "))
  & $Exe @args
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {
    throw "tailscale up failed with exit code $LASTEXITCODE"
  }
}

function Install-OpenSSH {
  Write-Step "Installing OpenSSH Server"
  $cap = Get-WindowsCapability -Online | Where-Object { $_.Name -like "OpenSSH.Server*" } | Select-Object -First 1
  if (-not $cap) {
    throw "OpenSSH.Server capability not found on this Windows edition."
  }
  if ($cap.State -ne "Installed") {
    Add-WindowsCapability -Online -Name $cap.Name | Out-Null
  }
  else {
    Write-Host "OpenSSH Server already installed."
  }

  Start-Service sshd -ErrorAction SilentlyContinue
  Set-Service -Name sshd -StartupType Automatic
  if ((Get-Service sshd).Status -ne "Running") {
    Start-Service sshd
  }

  $rule = Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue
  if (-not $rule) {
    New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" `
      -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
  }
  else {
    Enable-NetFirewallRule -Name "OpenSSH-Server-In-TCP" | Out-Null
  }
}

function Merge-AuthorizedKeys([string]$Path, [string[]]$Keys) {
  $dir = Split-Path -Parent $Path
  if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }

  $existing = @()
  if (Test-Path -LiteralPath $Path) {
    $existing = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue |
      ForEach-Object { $_.Trim() } |
      Where-Object { $_ -and -not $_.StartsWith("#") }
  }

  $merged = New-Object System.Collections.Generic.List[string]
  foreach ($line in $existing) { [void]$merged.Add($line) }
  foreach ($key in $Keys) {
    $k = $key.Trim()
    if (-not $k -or $k.StartsWith("#")) { continue }
    if ($merged -notcontains $k) { [void]$merged.Add($k) }
  }

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllLines($Path, $merged.ToArray(), $utf8NoBom)
}

function Set-AdministratorsAuthorizedKeysAcl([string]$Path) {
  # OpenSSH on Windows requires SYSTEM + Administrators only on this file.
  icacls $Path /inheritance:r | Out-Null
  icacls $Path /grant "System:(F)" | Out-Null
  icacls $Path /grant "Builtin\Administrators:(F)" | Out-Null
}

function Install-AuthorizedKeys([string]$Base) {
  Write-Step "Installing KCW SSH public keys"
  if (-not $Base) {
    throw "BaseUrl is required to download authorized_keys."
  }
  $url = ($Base.TrimEnd("/") + "/tools/windows-remote/files/authorized_keys")
  $tmp = Join-Path $env:TEMP ("kcw-authorized-keys-" + [guid]::NewGuid().ToString("N") + ".txt")
  try {
    Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing
    $keys = Get-Content -LiteralPath $tmp |
      ForEach-Object { $_.Trim() } |
      Where-Object { $_ -and -not $_.StartsWith("#") }
    if (-not $keys) {
      throw "authorized_keys download was empty: $url"
    }

    $userKeys = Join-Path $env:USERPROFILE ".ssh\authorized_keys"
    Merge-AuthorizedKeys -Path $userKeys -Keys $keys
    Write-Host "Updated $userKeys"

    $adminKeys = "C:\ProgramData\ssh\administrators_authorized_keys"
    Merge-AuthorizedKeys -Path $adminKeys -Keys $keys
    Set-AdministratorsAuthorizedKeysAcl -Path $adminKeys
    Write-Host "Updated $adminKeys"
  }
  finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
  }
}

function Show-Summary([string]$Exe) {
  Write-Step "Done"
  $user = $env:USERNAME
  $ip = ""
  $dns = ""
  try {
    $ip = (& $Exe ip -4 2>$null | Select-Object -First 1).Trim()
  } catch {}
  try {
    $status = & $Exe status --json 2>$null | ConvertFrom-Json
    if ($status.Self.DNSName) { $dns = $status.Self.DNSName.TrimEnd(".") }
  } catch {}

  Write-Host ""
  Write-Host "Windows user : $user"
  if ($ip)  { Write-Host "Tailscale IP : $ip" }
  if ($dns) { Write-Host "MagicDNS    : $dns" }
  Write-Host ""
  Write-Host "From HQ, SSH with:"
  if ($dns) {
    Write-Host ("  ssh -i ~/.ssh/kcw-windows-remote {0}@{1}" -f $user, $dns)
  }
  elseif ($ip) {
    Write-Host ("  ssh -i ~/.ssh/kcw-windows-remote {0}@{1}" -f $user, $ip)
  }
  else {
    Write-Host ("  ssh -i ~/.ssh/kcw-windows-remote {0}@<tailscale-ip-or-name>" -f $user)
  }
  Write-Host ""
  Write-Host "Tell the admin the Tailscale name/IP above if they do not see the device yet."
}

Assert-Admin

if (-not $Hostname) {
  $Hostname = $env:COMPUTERNAME.ToLowerInvariant()
}

$tailscale = Install-Tailscale
Connect-Tailscale -Exe $tailscale -Key $AuthKey -TsHostname $Hostname
Install-OpenSSH
Install-AuthorizedKeys -Base $BaseUrl
Show-Summary -Exe $tailscale
