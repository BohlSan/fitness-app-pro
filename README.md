# Fitness App

Plataforma web para gestionar rutinas, registrar entrenamientos y analizar el progreso.
Stack: Python, FastAPI, SQLAlchemy ORM, PostgreSQL (Supabase), HTML/CSS/JS.

## Puesta en marcha local

1. Clonar el repositorio y entrar a la carpeta.
2. Crear y activar el entorno virtual:
   - Windows: `python -m venv .venv` y `.venv\Scripts\Activate.ps1`
   - Mac/Linux: `python3 -m venv .venv` y `source .venv/bin/activate`
3. Instalar dependencias: `pip install -r requirements.txt`
4. Copiar `.env.example` a `.env` y completar `DATABASE_URL`, `TEST_DATABASE_URL` y `SECRET_KEY`
   (usar la cadena del Session pooler de Supabase con prefijo `postgresql+psycopg://`).
5. Levantar la app: `uvicorn app.main:app --reload`
6. Probar: http://127.0.0.1:8000/health y http://127.0.0.1:8000/docs

## Tests

`pytest -v`  (usan `TEST_DATABASE_URL`, nunca la base de desarrollo)

## Estructura

- `app/db/registry.py`: registry y metadata de SQLAlchemy
- `app/database.py`: Engine, Session y dependencia `get_db`
- `app/models/`, `app/schemas/`, `app/routers/`, `app/services/`: capas del backend
- `app/static/`: frontend (HTML/CSS/JS)
- `tests/`: tests con pytest

