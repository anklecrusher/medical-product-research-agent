param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("test", "doctor")]
    [string] $Action
)

$ErrorActionPreference = "Stop"

switch ($Action) {
    "test" {
        & ".\.venv\Scripts\python.exe" -m pytest
    }
    "doctor" {
        & ".\.venv\Scripts\python.exe" --version
        & ".\.venv\Scripts\python.exe" -m pip --version
        if (Get-Command node -ErrorAction SilentlyContinue) {
            node --version
            npm --version
        }
        else {
            Write-Host "Node.js is not on PATH yet."
        }
    }
}

