$ErrorActionPreference = 'Stop'

$venvPython = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment not found at .venv. Run: & `"$env:LOCALAPPDATA\Programs\Python\Python312\python.exe`" -m venv .venv"
}

Write-Host "Run these commands in the current shell:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  python --version"
Write-Host "  python -m pytest"
