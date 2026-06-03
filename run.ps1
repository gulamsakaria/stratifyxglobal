$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    Write-Host "Creating virtual environment..."
    py -m venv .venv
}

& $python -m pip install -r requirements.txt
& $python -m streamlit run app.py
