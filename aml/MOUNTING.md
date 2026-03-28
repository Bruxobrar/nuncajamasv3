# Montaje: base + porta lámpara + pantalla (concepto)

## Objetivo
Estandarizar dónde va el porta lámpara y cómo se conecta la pantalla (modelo generado) con la base, para poder testear en la página y recomendar bases.

## Concepto (MVP)
- La pantalla define una interface mecánica en la boca.
  - `bayonet_female` cuando existe `socket_id`.
  - `ring` cuando existe `opening_radius`.
- La base aporta el porta lámpara y el adapter que calza con esa interface.
- El recomendador usa: tipo de interface + diámetro efectivo + catálogo.

## Endpoints
- `GET /api/bases/catalog`
- `POST /api/bases/recommend`

## Dashboard
- Panel “Base + Porta lámpara”: muestra interface detectada, sugiere bases y puede aplicar un `mount_profile` si el motor expone esos parámetros.

## Próximo paso
Agregar generadores reales y parámetros para `thread` (enrosque) y `press_fit` (click/presión).
