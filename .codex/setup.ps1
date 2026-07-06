$ErrorActionPreference = "Stop"

$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    $python = "python"
}

& $python -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -e ".[dev]"

New-Item -ItemType Directory -Force -Path data, outputs, cache, uploads | Out-Null

if (Test-Path -LiteralPath "package.json") {
    npm install
}

