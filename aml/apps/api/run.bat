@echo off
REM 1) Ir al directorio del script
cd /d "%~dp0"

REM 2) Crear venv si no existe
if not exist ".venv\Scripts\activate.bat" (
    echo Creando entorno virtual...
    python -m venv .venv
    if %ERRORLEVEL% neq 0 exit /b %ERRORLEVEL%
)

REM 3) Actualizar pip y instalar dependencias
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip install httpx

REM 4) Activar el entorno y ejecutar uvicorn (sin policy de PowerShell)
call .venv\Scripts\activate.bat
echo Entorno activado: %VIRTUAL_ENV%
echo Iniciando servidor en http://127.0.0.1:8000
start "" /b uvicorn main:app --reload --host 127.0.0.1 --port 8000

REM Esperar a que el servidor estÃ© listo
echo Esperando que el servidor inicie...
:wait_loop
timeout /t 1 /nobreak >nul
curl -s http://127.0.0.1:8000/ >nul 2>&1
if %ERRORLEVEL% neq 0 goto wait_loop

REM Abrir navegador
start "" "http://127.0.0.1:8000/"
