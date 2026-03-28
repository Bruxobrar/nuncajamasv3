# Ejecuta el entorno dev desde la raíz.
# Uso: PowerShell.exe -ExecutionPolicy Bypass -File .\scripts\dev.ps1

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $root '..')

PowerShell.exe -ExecutionPolicy Bypass -File .\apps\api\run.ps1