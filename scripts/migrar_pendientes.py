"""Migración manual de ejercicios por tiempo y carga automática de peso corporal.

Ejecutar una sola vez sobre cada base PostgreSQL existente:
    poetry run python -m scripts.migrar_pendientes

La migración es idempotente en cuanto a la creación de columnas. No borra datos.
"""
from sqlalchemy import text

from app.database import engine


SENTENCIAS = (
    "ALTER TABLE ejercicios ADD COLUMN IF NOT EXISTS tipo_medicion VARCHAR(20) NOT NULL DEFAULT 'REPETICIONES'",
    "ALTER TABLE ejercicios ADD COLUMN IF NOT EXISTS usa_peso_corporal BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE rutina_ejercicios ALTER COLUMN series DROP NOT NULL",
    "ALTER TABLE rutina_ejercicios ALTER COLUMN repeticiones DROP NOT NULL",
    "ALTER TABLE rutina_ejercicios ADD COLUMN IF NOT EXISTS duracion_sugerida_segundos INTEGER",
    "ALTER TABLE series ALTER COLUMN repeticiones DROP NOT NULL",
    "ALTER TABLE series ADD COLUMN IF NOT EXISTS duracion_segundos INTEGER",
)


def migrar() -> None:
    with engine.begin() as conexion:
        for sentencia in SENTENCIAS:
            conexion.execute(text(sentencia))
    print("Migración de ejercicios por tiempo y peso corporal aplicada correctamente.")


if __name__ == "__main__":
    migrar()