# 🎮 Pasapalabra Host Console - Versión Web

Una interfaz web moderna y elegante para controlar el juego de Pasapalabra.

## ✨ Características

- 🎯 **Interfaz moderna**: Diseño dark mode limpio y profesional
- ⚡ **Responsive**: Se adapta a cualquier tamaño de pantalla (desktop, tablet, mobile)
- 🔄 **Tiempo real**: Timer en vivo con actualizaciones por segundo
- 📊 **Estadísticas**: Comparativa de puntajes en tiempo real
- ⌨️ **Atajos de teclado**: Control rápido sin usar el ratón
- 🎨 **Animaciones suaves**: Interfaz fluida y agradable
- 🔌 **API REST**: Backend moderno con FastAPI
- 💻 **Full-stack**: Separación clara frontend/backend

## 🚀 Instalación Rápida

### Requisitos
- Python 3.8 o superior
- Un navegador web moderno (Chrome, Firefox, Edge, Safari)

### Opción 1: Batch Script (Windows)
Simplemente haz doble clic en `run.bat`:
```
cd directorio
run.bat
```
Se abrirá automáticamente en tu navegador.

### Opción 2: PowerShell Script (Windows)
```powershell
.\run.ps1
```

### Opción 3: Manual

1. **Crear entorno virtual:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
```

2. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

3. **Iniciar el servidor:**
```bash
python main.py
```

4. **Abrir en navegador:**
```
http://localhost:8000
```

## ⌨️ Controles

### Botones
- **✅ Correcta** - Marcar respuesta como correcta
- **⏭ Pasapalabra** - Pasar el turno
- **❌ Incorrecta** - Marcar respuesta como incorrecta
- **▶ Reanudar** - Iniciar o reanudar el juego
- **⇄ Cambiar vista** - Ver el rosco del otro jugador (en pausa)
- **↺ Reset partida** - Reiniciar todo

### Atajos de Teclado
| Tecla | Acción |
|-------|--------|
| `Espacio` | Reanudar/Iniciar |
| `V` | Correcta ✓ |
| `A` | Pasapalabra ↺ |
| `R` | Incorrecta ✗ |
| `C` | Cambiar vista |
| `Esc` | Reset |

## 📱 Interfaz

### Panel Izquierdo
- **Rosco animado**: Visualización del estado de todas las letras
- Colores por estado:
  - 🔵 Azul: Pendiente
  - 🟢 Verde: Correcta
  - 🟡 Amarillo: Pasapalabra
  - 🔴 Rojo: Incorrecta
- Animación de parpadeo en la letra actual

### Panel Derecho
- **Estado**: Modo actual (Pausa, En juego, Comparativa, Finalizado)
- **Acciones**: Botones de control
- **Puntaje**: Comparativa de scores
- **Configuración**: Nombres de jugadores y tiempo total

## 🔧 Configuración

Antes de empezar puedes:
1. Cambiar los nombres de los jugadores
2. Ajustar el tiempo total (30-600 segundos)
3. Hacer clic en "Aplicar y resetear"

## 🎮 Flujo de Juego

1. **Configurar**: Define nombres y tiempo
2. **Reset/Aplicar**: Inicia con los valores configurados
3. **Reanudar**: Comienza el juego
4. **Marcar respuesta**: Usa los botones o atajos
5. **Cambiar vista**: En pausa, mira el rosco del otro jugador
6. **Finalizar**: Cuando ambos terminen

## 📊 Información en Tiempo Real

El panel de la derecha muestra:
- **Turno real**: Quién está jugando ahora
- **Rosco visible**: Quién se ve en el canvas
- **Tiempo**: Cronómetro del jugador activo
- **Letra actual**: Letra que está respondiendo
- **Puntajes**: Correctas, Pasapalabras, Incorrectas, Pendientes

## 🚦 Estados del Juego

- **Pausa** (Azul): Esperando inicio o entre respuestas
- **En juego** (Verde): Partida en progreso, cronómetro corriendo
- **Consulta comparativa** (Amarillo): Viendo el rosco del otro en pausa
- **Partida finalizada** (Rojo): Ambos jugadores sin letras pendientes

## 🔗 URLs

- **API REST**: `http://localhost:8000/api`
- **Documentación API**: `http://localhost:8000/docs`
- **Frontend**: `http://localhost:8000`

## 📝 Endpoints API

- `GET /api/state` - Obtener estado actual
- `POST /api/config` - Actualizar configuración
- `POST /api/start-resume` - Iniciar/Reanudar
- `POST /api/pause` - Pausar
- `POST /api/mark-letter` - Marcar letra
- `POST /api/toggle-compare` - Cambiar vista
- `POST /api/reset` - Reset
- `POST /api/timer-tick` - Avanzar timer

## 🎨 Tema de Colores

Colores predefinidos en paleta dark mode:
- Fondo: `#0b1020` (Azul muy oscuro)
- Paneles: `#121a2f` / `#1a2440`
- Texto: `#eef3ff` (Blanco azulado)
- Acentos: `#69b7ff` (Azul)
- Estados: Verde, Amarillo, Rojo, Azul

## 📦 Estructura

```
pasapalabra-web/
├── backend/
│   ├── main.py           # Servidor FastAPI
│   ├── requirements.txt   # Dependencias Python
│   └── venv/             # Entorno virtual (se crea automáticamente)
├── frontend/
│   └── index.html        # Aplicación web (HTML + CSS + JS)
├── run.bat               # Iniciador para Windows
├── run.ps1               # Iniciador PowerShell
└── README.md             # Este archivo
```

## 🐛 Troubleshooting

### Puerto 8000 ya está en uso
Cierra otras aplicaciones que usen ese puerto o modifica el puerto en `backend/main.py` línea 209.

### Python no se encuentra
Asegúrate de tener Python instalado y en el PATH:
```bash
python --version
```

### El navegador no abre automáticamente
Abre manualmente: `http://localhost:8000`

### El timer no avanza
Verifica que el servidor esté corriendo sin errores en la consola.

## 💡 Tips

- Usa los atajos de teclado para ir más rápido
- En pausa, puedes ver el rosco del otro jugador con "⇄ Cambiar vista"
- El puntaje se actualiza en tiempo real
- La letra actual parpadea en la pantalla durante el juego
- Todos los datos se guardan en memoria local (aplicación stateless)

## 📄 Licencia

Basado en el código original de Pasapalabra Host Console

---

¡A disfrutar del Pasapalabra! 🎉
