#Requires -RunAsAdministrator
param([string] $ServerAddress = '192.168.10.163,192.168.10.13,192.168.43.12')

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../..')).Path
$publicKey = (Get-Content -LiteralPath (Join-Path $PSScriptRoot 'server_workstation.pub') -Raw).Trim()
if ($publicKey -notmatch '^ssh-ed25519 [A-Za-z0-9+/=]+ as2w-opencode-20261109$') {
    throw 'Unexpected server public key format'
}

$capability = Get-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0'
if ($capability.State -ne 'Installed') {
    Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Host
}

$sshDirectory = 'C:\ProgramData\ssh'
New-Item -ItemType Directory -Force -Path $sshDirectory | Out-Null
$authorizedKeys = Join-Path $sshDirectory 'administrators_authorized_keys'
if (-not (Test-Path -LiteralPath $authorizedKeys)) {
    [IO.File]::WriteAllText($authorizedKeys, "$publicKey`r`n", [Text.Encoding]::ASCII)
} elseif (-not (Get-Content -LiteralPath $authorizedKeys -Raw).Contains($publicKey)) {
    [IO.File]::AppendAllText($authorizedKeys, "$publicKey`r`n", [Text.Encoding]::ASCII)
}

& icacls.exe $authorizedKeys /inheritance:r /grant:r '*S-1-5-32-544:F' '*S-1-5-18:F' | Out-Host
if ($LASTEXITCODE -ne 0) { throw 'Could not set authorized_keys ACL' }

$standardRule = Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue
if ($standardRule) { Disable-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' }
$ruleName = 'AS2W-OpenCode-Workstation-SSH'
$remoteAddresses = $ServerAddress -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ }
if (-not (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -Name $ruleName -DisplayName 'AS2W OpenCode SSH from server' `
        -Direction Inbound -Protocol TCP -LocalPort 22 -RemoteAddress $remoteAddresses `
        -Profile Any -Action Allow | Out-Null
} else {
    # 服务器换 IP 时重跑本脚本即可，旧地址会保留为回退（用 -ServerAddress 覆盖全部）
    Set-NetFirewallRule -Name $ruleName -RemoteAddress $remoteAddresses
}

Set-Service -Name sshd -StartupType Automatic
Start-Service -Name sshd -ErrorAction SilentlyContinue
$service = Get-Service sshd
$listener = Get-NetTCPConnection -LocalPort 22 -State Listen -ErrorAction SilentlyContinue
if ($service.Status -ne 'Running' -or -not $listener) {
    throw 'sshd did not start listening on port 22'
}

$launcher = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'as2w_field.ps1'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'as2w_field.ps1') -Destination $launcher -Force

$logDir = Join-Path $projectRoot '部署测试/04_调试记录/logs'
$logFile = Join-Path $logDir ('{0}_workstation_ssh_setup.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
@(
    "time=$(Get-Date -Format o)"
    "server=$ServerAddress"
    "sshd=$($service.Status)"
    "port=22"
    "authorized_keys=$authorizedKeys"
    "launcher=$launcher"
    'auth=server ed25519 key; private key stays on server'
) | Set-Content -LiteralPath $logFile -Encoding UTF8
Write-Output "sshd is listening on port 22. Setup log: $logFile"
