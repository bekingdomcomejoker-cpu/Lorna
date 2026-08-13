@echo off
cd /d %~dp0
if exist .venv\Scripts\python.exe (
  set PY=.venv\Scripts\python.exe
) else (
  set PY=python
)
if not exist evidence_inbox mkdir evidence_inbox
if not exist reports mkdir reports
if not exist logs mkdir logs
%PY% -m census_engine run --db census.sqlite --input evidence_inbox --urls urls.txt --outdir reports
pause
