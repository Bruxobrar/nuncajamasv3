# Sistema de autenticación

## Usuarios de prueba

- Usuario: `admin`
- Contraseña: `admin123`

- Usuario: `user`
- Contraseña: `user123`

## Cómo agregar usuarios

Podés generar hashes bcrypt y agregarlos a `apps/api/users.json`.

```python
from passlib.context import CryptContext
import json

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

new_username = "nuevo_usuario"
new_password = "contraseña_segura"
hashed = pwd_context.hash(new_password)

with open("users.json", "r", encoding="utf-8") as f:
    users = json.load(f)

users[new_username] = hashed

with open("users.json", "w", encoding="utf-8") as f:
    json.dump(users, f, indent=2)
```

## Configuración

- `SECRET_KEY`: variable de entorno (obligatoria en producción).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: variable de entorno (default 30).

## Flujo

1. Visitar `/portal/`
2. Clic en "Ir al generador"
3. Login (`POST /token`)
4. Redirección a `/dashboard/` con JWT guardado en `localStorage`