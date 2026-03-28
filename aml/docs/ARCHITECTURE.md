# Arquitectura (visión)

## Objetivo

Proyecto hosteado donde un usuario compra **créditos/tokens** y los consume para **generar** y **exportar** geometría (`.stl` / `.3mf`).

## Apps

- `apps/api/` (FastAPI)
  - Auth JWT (`POST /token`)
  - Endpoints de generación/preview/export/import bajo `/api/*`
  - Sirve estáticos: `/portal/` y `/dashboard/`
- `apps/portal/` (landing)
- `apps/dashboard/` (UI técnica)

## Diseño del sistema de tokens (propuesto)

- **Unidad:** `credits` enteros (p.ej. 1 crédito por preview y 3 créditos por export final).
- **Ledger (recomendado):** tabla de movimientos (append-only) + balance derivado.
- **Reglas:**
  - `preview` puede ser gratis/limitado (rate limit) o consumir poco.
  - `export` siempre consume (y queda trazabilidad: `who`, `what`, `when`, `params_hash`).
- **Pago:** integrar proveedor (Stripe/MercadoPago) con webhook → acredita créditos.

## Persistencia/Storage (propuesto)

- Base de datos: Postgres (usuarios, ledger, exports metadata).
- Archivos exportados: S3/R2/Blob (o volumen persistente si self-hosted).

## Seguridad/Producción (mínimos)

- `SECRET_KEY` por variable de entorno (no hardcode).
- CORS restringido por dominio en producción.
- Rate limiting para `/token` y generación.
- Logs estructurados y métricas básicas.