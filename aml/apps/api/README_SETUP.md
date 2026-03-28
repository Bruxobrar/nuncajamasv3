# Setup rápido (API + Portal/Dashboard)

1. Abrir PowerShell o cmd
2. Ir a la carpeta:

   `cd C:\nuncajamasv3\aml\apps\api`

3. Ejecutar el script adecuado:

- en cmd:
  `run.bat`

- en PowerShell (sin cambiar política global):
  `powershell -ExecutionPolicy Bypass -File .\run.ps1`

---

El script hace:
- crea `.venv` si falta
- instala dependencias de `requirements.txt`
- inicia `uvicorn main:app --reload --host 127.0.0.1 --port 8000`

### Probar API

`curl http://127.0.0.1:8000/api/config`

### Abrir UI

`http://127.0.0.1:8000/` (redirige a `/portal/`)
