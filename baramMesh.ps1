# Launch baramMesh from this repo root using the local venv.
# Usage (PowerShell): .\baramMesh.ps1

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repoRoot

$activate = Join-Path $repoRoot 'venv\Scripts\Activate.ps1'
if (-not (Test-Path -LiteralPath $activate)) {
    throw "Virtual environment not found at: $activate`nCreate it with: python -m venv venv ; .\venv\Scripts\Activate.ps1 ; pip install -r requirements.txt"
}

. $activate

python -m baramMesh.main
