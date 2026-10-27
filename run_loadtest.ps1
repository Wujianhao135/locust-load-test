# ============================================================
# 若依性能压测：自动跑 3 个并发梯度（10 / 50 / 100 用户）
# 用法：
#   1. 先启动若依，确保浏览器能打开 http://localhost
#   2. 在本目录打开 PowerShell，运行：  .\run_loadtest.ps1
# 结果：reports/ 下生成每个梯度的 HTML 报告 + CSV 数据
# ============================================================

$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot
$py = "C:\Users\13500\anaconda3\python.exe"
New-Item -ItemType Directory -Force -Path "reports" | Out-Null

$gradients = @(
    @{ u = 10;  r = 2;  t = "20s" },
    @{ u = 50;  r = 5;  t = "20s" },
    @{ u = 100; r = 10; t = "20s" }
)

foreach ($g in $gradients) {
    $tag = "u$($g.u)"
    Write-Host "==================== 并发 $($g.u) 用户 ===================="
    & $py -m locust -f locustfile.py --headless --host http://localhost:8080 `
        -u $g.u -r $g.r -t $g.t `
        --html "reports/report_$tag.html" --csv "reports/$tag"
}

Write-Host ""
Write-Host "全部完成，结果在 reports/ 目录："
Write-Host "  report_u10.html / report_u50.html / report_u100.html"
Write-Host "  u10_stats.csv / u50_stats.csv / u100_stats.csv"
