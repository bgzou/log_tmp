$ErrorActionPreference = 'Stop'
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$project = Join-Path $root '部署参考\cpp_deploy-as2w'
$target = Join-Path $root '部署测试'
$packageDir = Join-Path $target '01_现场部署包'
$guideDir = Join-Path $target '02_现场操作'
$officialDir = Join-Path $target '03_官方资料'
New-Item -ItemType Directory -Force -Path $packageDir, $guideDir, $officialDir | Out-Null

# The deployment source has exactly one maintained copy in 部署参考/cpp_deploy-as2w.
& powershell -ExecutionPolicy Bypass -File (Join-Path $project 'tools\package_for_cpro.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Deployment package build failed' }

$packages = @('cpp_deploy-as2w.tar.gz', 'unitree_sdk2-src.tar.gz')
$sums = @()
foreach ($name in $packages) {
    $src = Join-Path $project "dist\$name"
    $dst = Join-Path $packageDir $name
    Copy-Item -LiteralPath $src -Destination $dst -Force
    $hash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash.ToLowerInvariant()
    $sums += "$hash  $name"
}
$sumsPath = Join-Path $packageDir 'SHA256SUMS.txt'
[IO.File]::WriteAllText($sumsPath, (($sums -join "`n") + "`n"), [Text.Encoding]::ASCII)

Copy-Item -LiteralPath (Join-Path $project 'README.md') -Destination (Join-Path $guideDir '部署工程说明.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'docs\official_findings.md') -Destination (Join-Path $guideDir '宇树资料核对.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'docs\cpro_colleague_questions.md') -Destination (Join-Path $guideDir 'CPRO同事问题.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'docs\policy_testing.md') -Destination (Join-Path $guideDir '策略选择与测试.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'docs\architecture.md') -Destination (Join-Path $guideDir '部署架构.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'docs\go2_deploy_audit.md') -Destination (Join-Path $guideDir 'GO2文件移植判断.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'config\hardware_contract.md') -Destination (Join-Path $guideDir '低层硬件合同.md') -Force
Copy-Item -LiteralPath (Join-Path $project 'config\calibrated.map.example') -Destination (Join-Path $guideDir 'calibrated.map.example') -Force

$officialSource = Join-Path $root '部署参考\宇树官方参考'
$pages = @(
    '关于As2W', 'As2W快速开始', 'As2W遥控器说明', '快速开发',
    '拓展坞使用说明', 'DDS通信接口', '底层服务接口',
    'As2W轮足运动服务接口', '运控切换服务接口', '设备状态服务接口'
)
foreach ($page in $pages) {
    Copy-Item -LiteralPath (Join-Path $officialSource "$page.html") -Destination $officialDir -Force
    $assets = Join-Path $officialSource "${page}_files"
    if (Test-Path -LiteralPath $assets) {
        Copy-Item -LiteralPath $assets -Destination $officialDir -Recurse -Force
    }
}

Write-Output "Field package ready: $target"
Get-Content -LiteralPath (Join-Path $packageDir 'SHA256SUMS.txt')
