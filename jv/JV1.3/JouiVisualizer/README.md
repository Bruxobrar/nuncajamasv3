# JouiVisualizer

MVP local para explorar `lampgen/pb6.py` con preview 3D en tiempo casi real y export STL.

## Arranque

```powershell
cd C:\nuncajamas\JouiVisualizer
python server.py
```

Abrir `http://127.0.0.1:8765`.

## Ejemplo desktop en Python

Si queres mover parametros en vivo desde Python, sin depender del navegador:

```powershell
cd C:\nuncajamas
python JouiVisualizer\live_tk.py
```

Ese ejemplo:

- Reusa la logica de `lampgen/pb6.py`.
- Replica presets y limites de `server.py`.
- Regenera el mesh en baja resolucion para preview interactivo.
- Permite exportar STL final desde la misma ventana.

## Que hace

- Usa `pb6` como motor de geometria.
- Genera preview interactivo con resolucion reducida.
- Exporta STL final a `JouiVisualizer/exports`.
- Incluye presets base para arrancar rapido.

## Limites actuales

- Solo envuelve `pb6`.
- El visor 3D esta hecho en `canvas` 2D, sin librerias externas.
- La iluminacion y el render son simples; la prioridad fue velocidad de entrega.
