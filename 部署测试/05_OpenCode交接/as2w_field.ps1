param(
    [Parameter(Mandatory = $true)] [string] $Stage,
    [string] $Model = 'all',
    [int] $Seconds = 5,
    [int] $Iterations = 3000
)

$ErrorActionPreference = 'Stop'
$entry = 'D:\Projects\Athena\运动控制\Collie\AS2-W_CPRO\部署测试\现场入口.ps1'
& $entry -Stage $Stage -Model $Model -Seconds $Seconds -Iterations $Iterations
if (-not $?) { exit 1 }
