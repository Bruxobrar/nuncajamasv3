# Levanta el API (sirve /portal/ y /dashboard/) sin tocar ExecutionPolicy global.
# Uso: PowerShell.exe -ExecutionPolicy Bypass -File .\run.ps1

$ErrorActionPreference = 'Stop'

try {
  $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
  Set-Location $scriptDir

  if (-not (Test-Path '.venv\Scripts\Activate.ps1')) {
    Write-Host 'Creando entorno virtual...'
    python -m venv .venv
  }

  . .\.venv\Scripts\Activate.ps1

  Write-Host "Entorno activado: $env:VIRTUAL_ENV"
  .venv\Scripts\python.exe -m pip install --upgrade pip
  .venv\Scripts\python.exe -m pip install -r requirements.txt

  Write-Host 'Iniciando servidor...'
  $python = Join-Path $scriptDir '.venv\Scripts\python.exe'
  $args = @('-m','uvicorn','main:app','--reload','--host','127.0.0.1','--port','8000')
  Start-Process -FilePath $python -ArgumentList $args -WorkingDirectory $scriptDir | Out-Null

  Write-Host 'Esperando que el servidor inicie...'
  do {
    Start-Sleep -Seconds 1
    try {
      Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/' -UseBasicParsing -TimeoutSec 2 | Out-Null
      $ready = $true
    } catch {
      $ready = $false
    }
  } while (-not $ready)

  Start-Process 'http://127.0.0.1:8000/'
} catch {
  Write-Error $_.Exception.Message
  exit 1
}
