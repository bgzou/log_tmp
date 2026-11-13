$ErrorActionPreference = 'Stop'
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$dist = Join-Path $project 'dist'
New-Item -ItemType Directory -Force -Path $dist | Out-Null
Push-Location $project
try {
    python tools/check_models.py
    if ($LASTEXITCODE -ne 0) { throw 'Model check failed' }
    $archive = Join-Path $dist 'cpp_deploy-as2w.tar.gz'
    tar.exe -czf $archive --exclude='tools/__pycache__' CMakeLists.txt README.md .gitignore src deploy tools config models docs/official_findings.md docs/cpro_colleague_questions.md docs/policy_testing.md docs/architecture.md docs/go2_deploy_audit.md
    if ($LASTEXITCODE -ne 0) { throw 'tar failed' }
    Get-FileHash -LiteralPath $archive -Algorithm SHA256 | Format-List
    Write-Output "Package ready: $archive"
    $sdk = Join-Path $project '..\unitree_sdk2'
    if (Test-Path -LiteralPath $sdk) {
        $sdkArchive = Join-Path $dist 'unitree_sdk2-src.tar.gz'
        tar.exe -czf $sdkArchive --exclude='unitree_sdk2/.git' -C (Split-Path $sdk -Parent) unitree_sdk2
        if ($LASTEXITCODE -ne 0) { throw 'SDK2 tar failed' }
        Get-FileHash -LiteralPath $sdkArchive -Algorithm SHA256 | Format-List
        Write-Output "SDK2 package ready: $sdkArchive"
    }
} finally {
    Pop-Location
}
