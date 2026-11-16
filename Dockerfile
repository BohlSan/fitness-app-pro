# syntax=docker/dockerfile:1

# ---------- Etapa 1: instalar dependencias con Poetry ----------
FROM python:3.14-slim AS builder

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN pip install "poetry>=2.0,<3.0"

WORKDIR /app

# Se copian primero solo los archivos de dependencias para aprovechar la caché de capas
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root


# ---------- Etapa 2: imagen final (sin Poetry ni herramientas de build) ----------
FROM python:3.14-slim

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Usuario sin privilegios: la aplicación no corre como root
RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY scripts ./scripts

USER appuser

EXPOSE 8000

# /health responde 503 si no hay conexión con la base, y eso marca el contenedor como "unhealthy"
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8000'))"]

# Respeta $PORT (Render lo define); por defecto 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]