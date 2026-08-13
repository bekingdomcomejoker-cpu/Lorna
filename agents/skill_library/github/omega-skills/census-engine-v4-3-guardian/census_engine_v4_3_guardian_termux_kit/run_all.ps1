$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PY = ".\.venv\Scripts\python.exe"
if (!(Test-Path $PY)) { $PY = "python" }
New-Item -ItemType Directory -Force evidence_inbox,reports,exports,logs | Out-Null
& $PY -m census_engine run --db census.sqlite --input evidence_inbox --urls urls.txt --outdir reports | Tee-Object -FilePath ("logs\run_all_{0}.json" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
Write-Host "Done. Open reports\evidence_report.md and reports\evidence_graph.graphml"
