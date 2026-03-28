# 🌌 ATLAS MULTIVERSAL - Ecosistema Web v1.0

Bienvenido al laboratorio de desarrollo de **Atlas Multiversal**. Este proyecto integra nuestros scripts de diseño generativo (Python) con una interfaz moderna y futurista.

## 📁 Estructura del Proyecto

- **/portal/**: Página A (Landing Page). Estética impactante y presentación del concepto.
- **/dashboard/**: Página B (Panel de Control). Interfaz técnica para previsualización 3D y generación de parámetros.
- **/backend/**: Servidor FastAPI que conecta la web con los motores de geometría.
  - **/generators/**: Aquí residen los scripts originales del HDD (lampgen, dronegen, planetgen).

## 🚀 Cómo Empezar

### 1. Requisitos
- Python 3.10+
- Extensiones de VS Code recomendadas: **Live Server**, **Python**, **GitHub Copilot**.

### 2. Ejecutar el Frontend
Para ver las páginas web:
1. Abre esta carpeta en VS Code.
2. Haz clic derecho en `/portal/index.html` -> **Open with Live Server**.
3. Haz lo mismo para `/dashboard/index.html`.

### 3. Ejecutar el Backend (API)
Desde la terminal en la carpeta `/backend/`:
```bash
pip install fastapi uvicorn
python main.py
```
La API estará disponible en `http://localhost:8000`.

## 🛠️ Notas para el Equipo (Copilot Ready)
- El código usa **CSS Variables** (`:root`) para mantener la consistencia del color neón.
- El JavaScript está modularizado y usa `fetch()` para comunicarse con el backend.
- **Visualización 3D**: Pendiente integrar `Three.js` en el dashboard para renderizar los `.stl` que generan los scripts en `/generators/`.

---
*Mantenimiento: Agente de Monitoreo de Seguridad Activo (WSL-Ubuntu)*
