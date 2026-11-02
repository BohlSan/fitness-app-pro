# Fitness App

Plataforma web para gestionar rutinas de entrenamiento, registrar entrenamientos, analizar el progreso y,
con un rol de **Personal Trainer**, administrar clientes. Proyecto grupal de Programación II.

## Qué permite hacer

**Usuario particular**
- Registrarse e iniciar sesión, completar su perfil (datos físicos, objetivo, hidratación).
- Crear rutinas por día de la semana con ejercicios del catálogo (o propios).
- Entrenar desde una rutina o en estilo libre: series, pesos, repeticiones, cronómetro, agua, dificultad, cansancio y ánimo.
- Ver el historial (con calendario mensual), el progreso (peso, ejercicios, mejores marcas, estadísticas), su racha y su hidratación.
- Vincularse con un personal trainer mediante un código.

**Personal trainer**
- Código de enlace para sus clientes, solicitudes pendientes y clientes activos.
- Ver información básica, historial, rutinas asignadas y progreso de cada cliente.
- Asignar y modificar rutinas, y llevar el estado de la cuota y el historial de pagos.
- Recibir novedades cuando un cliente termina un entrenamiento (patrón Observer).

## Tecnologías

| Capa | Tecnología |
|---|---|
| Backend | Python 3, FastAPI |
| Datos | PostgreSQL (Supabase), SQLAlchemy ORM (declarativo con `registry`) |
| Frontend | HTML, CSS y JavaScript sin framework (servido por FastAPI), Chart.js |
| Tests | pytest |
| Dependencias | Poetry |
| Despliegue | Render |

## Puesta en marcha local

1. Requisitos: Python 3.11 o superior, [Poetry](https://python-poetry.org/), Git y una base PostgreSQL
   (el proyecto usa dos proyectos de Supabase: uno de desarrollo y uno de tests).
2. Clonar el repositorio e instalar dependencias:
   ```
   git clone <url-del-repositorio>
   cd fitness-app
   poetry install
   ```
3. Crear el archivo `.env` a partir de `.env.example` y completarlo:

   | Variable | Descripción |
   |---|---|
   | `DATABASE_URL` | Base de desarrollo. Cadena del *Session pooler* de Supabase con prefijo `postgresql+psycopg://` |
   | `TEST_DATABASE_URL` | Base **distinta** para los tests (se borran sus tablas en cada corrida) |
   | `SECRET_KEY` | Clave para firmar los tokens. Generar con `python -c "import secrets; print(secrets.token_urlsafe(48))"` |

4. Crear las tablas y cargar el catálogo de ejercicios:
   ```
   poetry run python -m scripts.create_tables
   poetry run python -m scripts.seed_ejercicios
   ```
5. Levantar la aplicación:
   ```
   poetry run uvicorn app.main:app --reload
   ```
   - Aplicación: http://127.0.0.1:8000
   - Documentación interactiva de la API: http://127.0.0.1:8000/docs
   - Estado del servicio: http://127.0.0.1:8000/health

## Tests

```
poetry run pytest -v
```

Cubren autenticación y roles, perfil, ejercicios, rutinas, entrenamientos, historial, estadísticas, racha,
hidratación, relación entrenador-cliente, permisos, Observer, cuenta y persistencia. Usan `TEST_DATABASE_URL`
y nunca la base de desarrollo.

## Scripts

| Comando | Para qué sirve |
|---|---|
| `python -m scripts.create_tables` | Crea las tablas que falten (no modifica las existentes) |
| `python -m scripts.seed_ejercicios` | Carga el catálogo base de ejercicios (se puede repetir) |
| `python -m scripts.reset_db` | **Borra y recrea** todas las tablas (pide confirmación) |
| `python -m scripts.migrar_etapa_8` | Agrega dos columnas a una base creada antes de la hidratación configurable |

## Estructura

```
app/
  main.py            aplicación FastAPI y registro de routers
  config.py          variables de entorno
  database.py        Engine, Session y dependencia get_db
  db/registry.py     registry y metadata de SQLAlchemy
  security.py        hash de contraseñas y tokens
  dependencies.py    usuario actual y control de roles
  models/            modelos ORM (tablas)
  schemas/           validación y formato de entrada y salida
  routers/           endpoints HTTP
  services/          lógica de negocio
  static/            frontend (páginas, css y js)
scripts/             creación de tablas y carga de datos
tests/               tests con pytest
docs/                documentación
```

## Documentación

- [Arquitectura](docs/arquitectura.md)
- [Modelo de datos](docs/modelo-de-datos.md)
- [Cobertura de requerimientos](docs/cobertura.md)
- [Guía de uso](docs/uso.md)
- [Despliegue en Render](docs/despliegue.md)