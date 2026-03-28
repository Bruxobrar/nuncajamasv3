# Pasapalabra Host Console - PowerShell Starter
# Este script inicia el backend y abre el frontend en el navegador

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Pasapalabra Host Console" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar si Python está instalado
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python encontrado: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python no está instalado o no está en el PATH" -ForegroundColor Red
    Write-Host "Por favor instala Python desde https://www.python.org/" -ForegroundColor Red
    Read-Host "Presiona Enter para salir"
    exit
}

# Ir al directorio del backend
$backendPath = Join-Path $PSScriptRoot "backend"
Push-Location $backendPath

# Crear venv si no existe
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual..."
    python -m venv venv
}

# Activar venv
& ".\venv\Scripts\Activate.ps1"

# Instalar dependencias
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
pip install -q -r requirements.txt

# Rutas
$frontendPath = Join-Path $PSScriptRoot "frontend\index.html"

Write-Host ""
Write-Host "Iniciando servidor Pasapalabra..." -ForegroundColor Green
Write-Host "El servidor estará disponible en: http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

# Abrir el navegador
Start-Process "http://localhost:8000"

# Ejecutar el servidor
python main.py

Pop-Location
