$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$PY = ".\.venv\Scripts\python.exe"
if (!(Test-Path $PY)) { $PY = "python" }
& $PY -m census_engine @args
