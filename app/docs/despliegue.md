# Despliegue en Render

La aplicación se despliega como un único *Web Service* de Render conectado a una base PostgreSQL en Supabase.
El frontend lo sirve la misma aplicación, así que no hay un segundo servicio.

## 1. Base de producción

Crear un proyecto de Supabase **separado** del de desarrollo (por ejemplo `fitness-prod`), para que los datos de
prueba no se mezclen con los de la demo. Copiar la cadena del **Session pooler** y cambiar el inicio por
`postgresql+psycopg://`, igual que en desarrollo. En *Project Settings → Data API* conviene desactivar la API REST.

## 2. Preparar la base desde la computadora

Las tablas y el catálogo se cargan una sola vez, apuntando temporalmente a la base de producción:

```
# Windows (PowerShell)
$env:DATABASE_URL = "postgresql+psycopg://<usuario>:<password>@<host>:5432/postgres"
poetry run python -m scripts.create_tables
poetry run python -m scripts.seed_ejercicios

# Mac / Linux
DATABASE_URL="postgresql+psycopg://..." poetry run python -m scripts.create_tables
DATABASE_URL="postgresql+psycopg://..." poetry run python -m scripts.seed_ejercicios
```

Una variable de entorno tiene prioridad sobre el `.env`. En PowerShell, cerrar esa terminal al terminar para no
dejar la variable apuntando a producción.

## 3. Crear el servicio en Render

1. En Render: **New → Web Service** y conectar el repositorio de GitHub.
2. **Runtime:** Python 3 (el runtime de Python es el que incluye Poetry).
3. **Build Command:**
   ```
   pip install poetry && poetry config virtualenvs.create false && poetry install --only main --no-root
   ```
4. **Start Command:**
   ```
   python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. **Health Check Path:** `/health`
6. **Variables de entorno:**

   | Variable | Valor |
   |---|---|
   | `DATABASE_URL` | La cadena de la base de **producción** |
   | `SECRET_KEY` | Una clave nueva y aleatoria (distinta de la de desarrollo) |
   | `PYTHON_VERSION` | Una versión completa compatible con `pyproject.toml` (la misma que usan localmente) |

   `TEST_DATABASE_URL` no hace falta en producción.
7. Elegir el plan y desplegar.

## 4. Verificar

- `https://<tu-servicio>.onrender.com/health` debe responder `{"status":"ok","database":"connected"}`.
- Registrar un usuario, completar el perfil y crear un entrenamiento.
- Registrar un trainer, vincular al usuario con el código y probar la asignación de una rutina.

## 5. Actualizar

Cada `push` a la rama configurada vuelve a desplegar si el despliegue automático está activado.
Si un cambio agrega tablas, ejecutar `create_tables` contra producción antes de publicarlo.
Si agrega columnas a tablas existentes, hace falta un script de migración como `scripts/migrar_etapa_8.py`.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Current Python version … is not allowed by the project` | Falta `PYTHON_VERSION` o no es compatible con el campo `python` de `pyproject.toml` |
| `The lock file is not compatible with the current version of Poetry` | Poetry viejo. El Build Command instala el más nuevo con `pip install poetry`; si persiste, regenerar `poetry.lock` |
| `poetry: command not found` | El servicio no usa el runtime de Python |
| `/health` responde 503 | La `DATABASE_URL` es incorrecta (revisar usuario `postgres.<ref>`, el prefijo `postgresql+psycopg://` y que sea el *Session pooler*) |
| La primera carga tarda | En planes gratuitos el servicio puede suspenderse por inactividad: abrir la página unos minutos antes de una demo |

Plan B si Poetry diera problemas en Render: generar un `requirements.txt` con el plugin `poetry-plugin-export`
(`poetry export -f requirements.txt --without-hashes -o requirements.txt`), subirlo y usar como Build Command
`pip install -r requirements.txt`.

## Lista de seguridad antes de presentar

- [ ] `SECRET_KEY` de producción distinta de la de desarrollo.
- [ ] El archivo `.env` **no** está en el repositorio.
- [ ] Data API de Supabase desactivada en el proyecto de producción.
- [ ] Contraseña de la base de producción guardada solo en Render y en un lugar privado del equipo.