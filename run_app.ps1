# Run with: right-click “Run with PowerShell” or:
# powershell -ExecutionPolicy Bypass -File .\run_app.ps1
param(
  [string]$CondaBat = "$env:USERPROFILE\miniforge3\condabin\conda.bat",
  [string]$EnvName  = "onecell",
  [int]$Port        = 8866
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$ipynb = Join-Path $PSScriptRoot "app.ipynb"
$py    = Join-Path $PSScriptRoot "one_cell_app.py"
$URL   = "http://127.0.0.1:$Port/voila/render/app.ipynb"

if (-not (Test-Path $ipynb)) { Write-Host "[ERROR] Missing app.ipynb in $PSScriptRoot" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $py))    { Write-Host "[ERROR] Missing one_cell_app.py in $PSScriptRoot" -ForegroundColor Red; exit 1 }
if (-not (Test-Path $CondaBat)) { Write-Host "[ERROR] Miniforge conda.bat not found at: $CondaBat" -ForegroundColor Red; exit 1 }

Write-Host "Using: $CondaBat"
Write-Host "Env:   $EnvName"
Write-Host "Port:  $Port"
Write-Host "URL:   $URL"
Write-Host ""

# Foreground so you can see errors; kernel forced; auth disabled
& $CondaBat run -n $EnvName python -m voila $ipynb `
  --port=$Port --ip=127.0.0.1 `
  --VoilaConfiguration.kernel_name=$EnvName `
  --ServerApp.token='' --ServerApp.password='' `
  --ServerApp.open_browser=False `
  --ServerApp.disable_check_xsrf=True `
  --debug
