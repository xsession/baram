# Launch baramEditor from this repo root using the local venv.
# Usage (PowerShell): .\baramEditor.ps1

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repoRoot

$activate = Join-Path $repoRoot 'venv\Scripts\Activate.ps1'
if (-not (Test-Path -LiteralPath $activate)) {
    throw "Virtual environment not found at: $activate`nCreate it with: .\bootstrap-dev.ps1"
}

. $activate

python -m baramEditor.main
