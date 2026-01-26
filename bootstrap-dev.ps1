# Bootstrap a local dev environment in ./venv and generate Qt resources.
# Usage: .\bootstrap-dev.ps1

[CmdletBinding()]
param(
  [string]$PythonExe,
  [switch]$SkipDocs,
  [switch]$SkipBuild,
  [switch]$RecreateVenv
)

$ErrorActionPreference = 'Stop'

function Invoke-Native {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Args
  )

  & $FilePath @Args
  if ($LASTEXITCODE -ne 0) {
    $joined = ($Args -join ' ')
    throw "Command failed (exit $LASTEXITCODE): $FilePath $joined"
  }
}

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $repoRoot

$pythonPrefixArgs = @()
if (-not $PythonExe) {
  $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
  if ($pyLauncher) {
    $PythonExe = 'py'
    $pythonPrefixArgs = @('-3.13')
  } else {
    $PythonExe = 'python'
  }
}

function Invoke-BootstrapPython {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
  Invoke-Native -FilePath $PythonExe @($pythonPrefixArgs + $Args)
}

function Get-PythonMajorMinor {
  param(
    [Parameter(Mandatory = $true)][string]$Exe,
    [string[]]$PrefixArgs = @()
  )

  $raw = (& $Exe @($PrefixArgs + @('-c', 'import sys; print(sys.version_info.major, sys.version_info.minor)')))
  if ($LASTEXITCODE -ne 0) {
    return $null
  }
  $text = ($raw -join "`n").Trim()
  if ($text -notmatch '^(\d+)\s+(\d+)$') {
    return $null
  }
  return @{ Major = [int]$Matches[1]; Minor = [int]$Matches[2]; Raw = $text }
}

$bootstrapVer = Get-PythonMajorMinor -Exe $PythonExe -PrefixArgs $pythonPrefixArgs
if (-not $bootstrapVer -and $PythonExe -eq 'py' -and ($pythonPrefixArgs -join ' ') -eq '-3.13') {
  # py launcher exists but 3.13 is not installed/registered.
  $PythonExe = 'python'
  $pythonPrefixArgs = @()
  $bootstrapVer = Get-PythonMajorMinor -Exe $PythonExe -PrefixArgs $pythonPrefixArgs
}
if (-not $bootstrapVer) {
  throw "Failed to run Python interpreter: $PythonExe $($pythonPrefixArgs -join ' ')"
}
if ($bootstrapVer.Major -ne 3 -or $bootstrapVer.Minor -lt 11 -or $bootstrapVer.Minor -gt 13) {
  throw (
    "Unsupported Python version ($($bootstrapVer.Major).$($bootstrapVer.Minor)). Use Python 3.11, 3.12, or 3.13. " +
    "On Windows, install Python 3.13 (or 3.12) and re-run, then run with -RecreateVenv if needed."
  )
}

if (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'venv'))) {
  Invoke-BootstrapPython -m venv venv
}

. .\venv\Scripts\Activate.ps1

$venvVer = Get-PythonMajorMinor -Exe 'python'
if (-not $venvVer) {
  throw "Failed to run venv Python (activation may have failed)."
}
if ($venvVer.Major -ne 3 -or $venvVer.Minor -lt 11 -or $venvVer.Minor -gt 13) {
  if (-not $RecreateVenv) {
    throw (
      "Your existing ./venv uses Python $($venvVer.Major).$($venvVer.Minor), which is unsupported. " +
      "Delete ./venv and rerun, or rerun with -RecreateVenv to rebuild it with Python 3.13 (or 3.12)."
    )
  }

  if (Get-Command deactivate -ErrorAction SilentlyContinue) {
    deactivate
  }
  Remove-Item -LiteralPath (Join-Path $repoRoot 'venv') -Recurse -Force
  Invoke-BootstrapPython -m venv venv
  . .\venv\Scripts\Activate.ps1
}

Invoke-Native -FilePath 'python' -m pip install --upgrade pip
Invoke-Native -FilePath 'python' -m pip install --only-binary=:all: -r requirements.txt

if (-not $SkipBuild) {
  Invoke-Native -FilePath 'python' -m pip install -r requirements-build.txt
}

if (-not $SkipDocs) {
  Invoke-Native -FilePath 'python' -m pip install -r requirements-docs.txt
}

# Generate resource_rc.py and *_ui.py
Invoke-Native -FilePath 'python' .\convertUi.py

Write-Output "Dev environment ready."
