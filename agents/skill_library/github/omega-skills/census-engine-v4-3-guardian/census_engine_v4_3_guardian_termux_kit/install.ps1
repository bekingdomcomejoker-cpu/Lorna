$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
if (Test-Path requirements.txt) { .\.venv\Scripts\python.exe -m pip install -r requirements.txt }
New-Item -ItemType Directory -Force evidence_inbox,reports,exports,logs | Out-Null
.\.venv\Scripts\python.exe -m census_engine init --db census.sqlite
Write-Host "Installed. Drop files into evidence_inbox then run .\run_all.ps1"
