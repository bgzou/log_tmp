# 恢复无线 HDC（CPRO 直连 8710）
# 用法：右键“使用 PowerShell 运行”，或在终端执行：
#   powershell -NoProfile -ExecutionPolicy Bypass -File .\恢复无线HDC.ps1
# 只做 tconn + 验证，不改任何配置、不重启任何服务。

$ErrorActionPreference = 'Continue'
$hdc = Join-Path $PSScriptRoot 'hdc_6.1.1.280\hdc.exe'
$target = '192.168.10.180:8710'

if (-not (Test-Path $hdc)) { Write-Host "找不到 hdc.exe: $hdc" -ForegroundColor Red; exit 1 }

Write-Host "== 1. 网络检查 ==" -ForegroundColor Cyan
$tcp = (Test-NetConnection 192.168.10.180 -Port 8710 -WarningAction SilentlyContinue).TcpTestSucceeded
Write-Host ("8710 可达: " + $tcp)
if (-not $tcp) {
    Write-Host "CPRO 的 8710 不可达：先查本机是否在 192.168.10.x、CPRO 是否联网/改过 IP。" -ForegroundColor Yellow
    exit 2
}

Write-Host "== 2. 重连 ==" -ForegroundColor Cyan
& $hdc tconn $target
Start-Sleep -Seconds 2

Write-Host "== 3. 结果 ==" -ForegroundColor Cyan
& $hdc list targets -v

$ok = ((& $hdc -t $target shell "echo HDC_OK" 2>&1 | Out-String).Trim())
if ($ok -match 'HDC_OK') {
    Write-Host "恢复成功。以后命令统一带 -t $target" -ForegroundColor Green
} else {
    Write-Host "tconn 未生效，输出：$ok" -ForegroundColor Red
    exit 3
}
