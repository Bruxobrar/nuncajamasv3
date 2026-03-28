# AML (Atlas Multiversal Lab)

Ecosistema web para **diseño generativo** (Python) + **UI** (portal/dashboard) + **API** (FastAPI) para generar y exportar geometría (`.stl` / `.3mf`).

## Estructura del repo

- `apps/api/`: FastAPI (auth + endpoints de generación/export + montaje de estáticos)
- `apps/portal/`: Landing / marketing (estático)
- `apps/dashboard/`: Panel técnico (estático) para preview + export
- `docs/`: documentación de arquitectura y roadmap
- `scripts/`: utilidades de desarrollo

## Desarrollo (local)

### Opción A: correr API (recomendado)

- PowerShell: `powershell -ExecutionPolicy Bypass -File .\apps\api\run.ps1`
- cmd: `apps\api\run.bat`

Abrir: `http://127.0.0.1:8000/` (redirige a `/portal/`).

### Opción B: Docker

- `docker compose up --build`

Abrir: `http://127.0.0.1:8000/`.

## Notas de producto

- El login actual entrega un JWT vía `POST /token`.
- El dashboard usa ese JWT en `Authorization: Bearer <token>`.

Siguiente paso (producto): sistema de **tokens/créditos** para limitar `generate/export` a usuarios pagos. Ver `docs/ARCHITECTURE.md`.
