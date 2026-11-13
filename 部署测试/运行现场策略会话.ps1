param(
    [ValidateSet('r214','r1199','r4000','getup1199')]
    [string] $Policy = 'r214',
    [ValidateSet('stand','zero-b','motion','forward','forward-dry-run','joystick','joystick-dry-run','training-contract','training-contract-dry-run','r4000','r4000-dry-run','getup','getup-dry-run','dry-run')]
    [string] $Mode = 'dry-run',
    [ValidateRange(10, 300)]
    [int] $MonitorSeconds = 150,
    [string] $Target = '192.168.10.180:8710',
    [switch] $ConfirmMotion,
    [switch] $Debug,
    [ValidateRange(0, 200)]
    [int] $LowPassMs = 0,
    [switch] $LowPassWheels
)

$ErrorActionPreference = 'Stop'
$testRoot = $PSScriptRoot
$hdc = (Resolve-Path -LiteralPath (Join-Path $testRoot '00_HDC工具/hdc_6.1.1.280/hdc.exe')).Path
$logRoot = Join-Path $testRoot '04_调试记录/logs'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$localLog = Join-Path $logRoot "${stamp}_windows_${Policy}_${Mode}_field_session.log"

if ($Mode -notin @('dry-run','forward-dry-run','joystick-dry-run','training-contract-dry-run','r4000-dry-run','getup-dry-run') -and -not $ConfirmMotion) {
    throw "Mode '$Mode' can move the robot. Re-run only after the field action has been reviewed, adding -ConfirmMotion."
}
if ($Policy -eq 'r1199' -and $Mode -notin @('dry-run','zero-b','forward-dry-run','forward','joystick','joystick-dry-run','training-contract','training-contract-dry-run')) {
    throw "R1199 permits dry-run, bounded zero-b, the isolated bounded forward trial, or the isolated training-contract candidate only."
}
if ($Policy -eq 'r1199' -and $Mode -eq 'joystick') {
    throw "R1199 old joystick mode is paused after two real rolling-jitter/posture-jump trials. Use the separately built, separately reviewed 'training-contract' candidate instead; never bypass this launcher."
}
if ($Policy -eq 'r214' -and $Mode -in @('forward','forward-dry-run','joystick','joystick-dry-run')) {
    throw "The forward trial is R1199-specific."
}
if ($Policy -eq 'r4000' -and $Mode -notin @('r4000','r4000-dry-run','dry-run')) {
    throw "R4000 permits only the bounded r4000 candidate or its dry-run; use -Policy r4000 -Mode r4000|r4000-dry-run."
}
if ($Policy -ne 'r4000' -and $Mode -in @('r4000','r4000-dry-run')) {
    throw "Mode r4000 requires -Policy r4000."
}
if ($Policy -eq 'getup1199' -and $Mode -notin @('getup','getup-dry-run','dry-run')) {
    throw "getup1199 permits only the bounded getup chain or its dry-run; use -Policy getup1199 -Mode getup|getup-dry-run."
}
if ($Policy -ne 'getup1199' -and $Mode -in @('getup','getup-dry-run')) {
    throw "Mode getup requires -Policy getup1199."
}
if ($LowPassMs -gt 0 -and $Policy -eq 'getup1199') {
    throw 'Getup has no filtered candidate; the low-pass option does not apply.'
}
if ($LowPassMs -gt 0 -and ($Policy -ne 'r1199' -or $Mode -notin @('training-contract','training-contract-dry-run'))) {
    throw 'Filtered candidate currently exists only for R1199 training-contract. Other policies need their own isolated filtered build and offline validation.'
}
if ($LowPassWheels -and $LowPassMs -eq 0) { throw '-LowPassWheels requires -LowPassMs.' }
if ($LowPassMs -gt 0 -and $Mode -eq 'training-contract') {
    if ($LowPassMs -ne 40 -or $LowPassWheels -or -not $Debug) {
        throw 'Filtered motion permits only the reviewed R1199 40ms leg-only Debug candidate; other filter settings remain locked.'
    }
}
if ($Debug -and $Policy -eq 'r1199' -and $Mode -notin @('training-contract','training-contract-dry-run')) {
    throw 'The R1199 debug-enabled launcher currently supports only the training-contract candidate.'
}

$targets = @(& $hdc list targets 2>&1 | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
if ($targets -notcontains $Target) {
    Write-Host "HDC target $Target is absent; attempting tconn..."
    & $hdc tconn $Target
    if ($LASTEXITCODE -ne 0) { throw "hdc tconn failed for $Target" }
    $targets = @(& $hdc list targets 2>&1 | ForEach-Object { ([string]$_).Trim() } | Where-Object { $_ })
    if ($targets -notcontains $Target) { throw "HDC target still absent after tconn: $Target" }
}

$remoteScript = "tools/run_${Policy}_field_session.sh"
$remoteOptions = ''
if ($Policy -eq 'r4000') {
    # R4000 sessions always record the full debug chain (new policy, first
    # tiers); the launcher enforces this CPRO-side as well.
    $remoteOptions += ' --debug'
}
if ($Policy -eq 'getup1199') {
    # getup1199 motion sessions always record the full debug chain; the
    # CPRO launcher enforces this as well.
    $remoteOptions += ' --debug'
}
if ($Debug) { $remoteOptions += ' --debug' }
if ($LowPassMs -gt 0) { $remoteOptions += " --lowpass-ms $LowPassMs" }
if ($LowPassWheels) { $remoteOptions += ' --lowpass-wheels' }
$remote = "/data/local/tmp/as2w_field/cpro_ubuntu.sh /bin/bash -lc 'cd /root/as2w_deploy && bash $remoteScript $Mode $MonitorSeconds$remoteOptions'"
Write-Host "Target: $Target"
Write-Host "Remote: /root/as2w_deploy/$remoteScript $Mode $MonitorSeconds$remoteOptions"
Write-Host "Local transcript: $localLog"

$output = New-Object 'System.Collections.Generic.List[string]'
& $hdc -t $Target shell $remote 2>&1 | ForEach-Object {
    $line = [string]$_
    $output.Add($line)
    $line
} | Tee-Object -FilePath $localLog
$hdcRc = $LASTEXITCODE

$sessionDir = $null
foreach ($line in $output) {
    if ([string]$line -match 'dir=(/root/field_sessions/[^ ]+)') {
        $sessionDir = $Matches[1]
        break
    }
}

if ($sessionDir) {
    $sessionName = Split-Path -Leaf $sessionDir
    $fieldRoot = Join-Path $logRoot 'field_sessions'
    New-Item -ItemType Directory -Path $fieldRoot -Force | Out-Null
    $remoteHostPath = $sessionDir -replace '^/root/', '/data/ubuntu_in_hm/ubuntu_rootfs/root/'
    Write-Host "Receiving CPRO session archive: $remoteHostPath"
    & $hdc -t $Target file recv $remoteHostPath $fieldRoot
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Session ran, but automatic archive retrieval failed. Retrieve manually: $remoteHostPath"
    } else {
        Write-Host "Local session archive: $(Join-Path $fieldRoot $sessionName)"
    }
}

if ($hdcRc -ne 0) {
    throw "Field session transport/process failed (hdc exit $hdcRc). See $localLog"
}
if ($output | Where-Object { $_ -match '(^|\s)FATAL:' }) {
    throw "Remote field preflight/session reported FATAL. See $localLog"
}
if (-not ($output | Select-String -SimpleMatch 'session complete') -and $Mode -notin @('dry-run','forward-dry-run','joystick-dry-run','training-contract-dry-run','r4000-dry-run','getup-dry-run')) {
    throw "The remote script did not report session completion. See $localLog"
}
Write-Host "Done. Append the operator's observed robot behavior and these log paths to 04_调试记录/INDEX.md."
