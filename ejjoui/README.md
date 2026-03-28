# ejjoui

App de escritorio para explorar y exportar los motores de modelos que ya existen en `lampgen`, sin navegador ni servidor local.

## Correr

```powershell
cd C:\nuncajamas\ejjoui
python app.py
```

O en Windows:

```powershell
cd C:\nuncajamas\ejjoui
.\run.bat
```

## Empaquetar como EXE

Si ya tenes `pyinstaller` instalado:

```powershell
cd C:\nuncajamas\ejjoui
.\build_exe.bat
```

El ejecutable queda en `dist\ejjoui.exe`.

## Qué reutiliza

- La configuración multi-engine de `JouiVisualizer/server.py`
- Los generadores STL de `lampgen`
- Preview 3D local en `tkinter`

## Nota

Por ahora exporta STL y guarda por defecto en `C:\nuncajamas\ejjoui\exports`.
