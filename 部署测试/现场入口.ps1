param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Sync','NetworkStatus','NetworkApply','Build','SdkBuild','PolicyList','PolicyVerify','PolicyBench','SportState','LowState','LowRemote','LowCapture','LowCaptureFast','LowProtection','MotionMode','ServiceList','GetState','PackageVersion','Shadow','LowCrc','MotionRelease','MotionSelect','R152Build','R152Replay','R152Shadow','R214Build','R214Replay','R214Shadow')]
    [string] $Stage,
    [string] $Model = 'all',
    [ValidateRange(1, 300)] [int] $Seconds = 5,
    [ValidateRange(1, 1000000)] [int] $Iterations = 3000
)

$ErrorActionPreference = 'Stop'
$testRoot = $PSScriptRoot
$root = (Resolve-Path -LiteralPath (Join-Path $testRoot '..')).Path
$hdc = (Resolve-Path -LiteralPath (Join-Path $testRoot '00_HDC工具/hdc_6.1.1.280/hdc.exe')).Path
$packageDir = (Resolve-Path -LiteralPath (Join-Path $testRoot '01_现场部署包')).Path
$logDir = Join-Path $testRoot '04_调试记录/logs'
$remoteDir = '/data/local/tmp/as2w_field'
$remoteHelper = "$remoteDir/cpro_ubuntu.sh"

function Invoke-HdcShell([string] $RemoteCommand) {
    $lines = @(& $hdc shell $RemoteCommand 2>&1)
    $rc = $LASTEXITCODE
    if ($rc -ne 0) { throw "HDC shell failed (exit $rc)" }
    return $lines
}

if ($Stage -eq 'Sync') {
    $syncLog = Join-Path $logDir ('{0}_windows_Sync.log' -f (Get-Date -Format 'yyyyMMdd-HHmmss'))
    [IO.File]::WriteAllText($syncLog, "Sync started: $(Get-Date -Format o)`r`n", [Text.UTF8Encoding]::new($true))
    function Write-SyncLines($Lines) {
        $items = @($Lines | ForEach-Object { [string] $_ })
        if ($items.Count -eq 0) { return }
        $items | ForEach-Object { Write-Output $_ }
        [IO.File]::AppendAllText($syncLog, (($items -join "`r`n") + "`r`n"), [Text.UTF8Encoding]::new($false))
    }
    $prepare = @(& powershell.exe -ExecutionPolicy Bypass -File (Join-Path $testRoot '准备现场包.ps1') 2>&1)
    Write-SyncLines $prepare
    if ($LASTEXITCODE -ne 0) { throw 'Package preparation failed' }
    foreach ($name in @('cpp_deploy-as2w.tar.gz', 'unitree_sdk2-src.tar.gz', 'SHA256SUMS.txt')) {
        $source = (Resolve-Path -LiteralPath (Join-Path $packageDir $name)).Path
        Write-SyncLines @(& $hdc file send $source "$remoteDir/" 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "HDC transfer failed: $name" }
    }
    foreach ($name in @('cpro_ubuntu.sh', 'cpro_host_net.sh')) {
        $source = (Resolve-Path -LiteralPath (Join-Path $root "部署参考/cpp_deploy-as2w/tools/$name")).Path
        Write-SyncLines @(& $hdc file send $source "$remoteDir/" 2>&1)
        if ($LASTEXITCODE -ne 0) { throw "HDC transfer failed: $name" }
    }
    $check = Invoke-HdcShell "cd $remoteDir && sha256sum -c SHA256SUMS.txt"
    Write-SyncLines $check
    if (@($check | Select-String ': OK$').Count -ne 2) { throw 'Remote SHA-256 verification failed' }
    Invoke-HdcShell "tar -xzf $remoteDir/cpp_deploy-as2w.tar.gz -C /data/ubuntu_in_hm/ubuntu_rootfs/root/as2w_deploy" | Out-Null
    Invoke-HdcShell "chmod 755 $remoteHelper $remoteDir/cpro_host_net.sh" | Out-Null
    Write-SyncLines "Sync finished: $(Get-Date -Format o)"
    Write-Output "CPRO source synced. Run -Stage SdkBuild before SDK2 diagnostics. Local log: $syncLog"
    return
}

if ($Stage -eq 'NetworkStatus' -or $Stage -eq 'NetworkApply') {
    $mode = if ($Stage -eq 'NetworkApply') { 'apply' } else { 'status' }
    $remote = "sh $remoteDir/cpro_host_net.sh $mode"
} else {
    if ($Model -notmatch '^[A-Za-z0-9_-]+$') { throw 'Invalid model name' }
    $stageArgs = switch ($Stage) {
        Build          { 'build' }
        SdkBuild       { 'sdk-build /root/unitree_sdk2_install' }
        PolicyList     { 'policy-list' }
        PolicyVerify   { "policy-verify $Model" }
        PolicyBench    { "policy-bench $Model $Iterations" }
        SportState     { "sport-state eth0 $Seconds" }
        LowState       { "low-state eth0 $Seconds" }
        LowRemote      { "low-remote eth0 $Seconds" }
        LowCrc         { "low-crc eth0 $Seconds" }
        LowCapture     { "low-capture eth0 $Seconds" }
        LowCaptureFast { "low-capture eth0 $Seconds rt/lowstate 10" }
        LowProtection { "low-protection eth0 $Seconds" }
        Shadow         { "policy-shadow $Model eth0 config/hypothesis.map $Seconds" }
        R152Build      { "r152-build /root/unitree_sdk2_install /root/ort122" }
        R152Replay     { "r152-replay" }
        R152Shadow     { "r152-shadow eth0" }
        R214Build      { "r214-build /root/unitree_sdk2_install /root/ort122" }
        R214Replay     { "r214-replay" }
        R214Shadow     { "r214-shadow eth0" }
        MotionMode     { 'motion-mode eth0' }
        MotionRelease  { 'motion-release eth0' }
        MotionSelect   { "motion-select eth0 $Model" }
        ServiceList    { 'service-list eth0' }
        GetState       { 'sport-command eth0 get-state' }
        PackageVersion { 'package-version eth0' }
    }
    $remote = "$remoteHelper /bin/bash /root/as2w_deploy/tools/field.sh $stageArgs"
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$log = Join-Path $logDir "${stamp}_windows_${Stage}.log"
$output = Invoke-HdcShell $remote
$output | ForEach-Object { Write-Output $_ }
$output | Set-Content -LiteralPath $log -Encoding UTF8
if ($Stage -ne 'NetworkStatus' -and $Stage -ne 'NetworkApply') {
    $lastExit = @($output | Select-String '^Exit code: (-?\d+)$' | Select-Object -Last 1)
    if ($lastExit.Count -ne 1 -or $lastExit[0].Matches[0].Groups[1].Value -ne '0') {
        throw "Remote stage did not complete successfully; see $log"
    }
}
Write-Output "Local log: $log"
