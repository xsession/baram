# Bootstrap a local dev environment in ./venv and generate Qt resources.
# Usage: .\bootstrap-dev.ps1

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repoRoot

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'venv'))) {
  python -m venv venv
}

. .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Generate resource_rc.py and *_ui.py
python .\convertUi.py

Write-Output "Dev environment ready."
