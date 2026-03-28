@echo off
REM Pasapalabra Host Console - Windows Batch Starter
REM Este script inicia el backend y abre el frontend en el navegador

cls
echo.
echo ========================================
echo   Pasapalabra Host Console
echo ========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python no está instalado o no está en el PATH
    echo Por favor instala Python desde https://www.python.org/
    pause
    exit /b 1
)

REM Ir al directorio del backend
cd /d "%~dp0backend"

REM Crear venv si no existe
if not exist "venv" (
    echo Creando entorno virtual...
    python -m venv venv
)

REM Activar venv
call venv\Scripts\activate.bat

REM Instalar dependencias
echo Instalando dependencias...
pip install -q -r requirements.txt

REM Iniciar el servidor FastAPI
echo.
echo Iniciando servidor Pasapalabra...
echo El servidor estará disponible en: http://localhost:8000
echo.

start http://localhost:8000

REM Ejecutar el servidor
python main.py

pause
