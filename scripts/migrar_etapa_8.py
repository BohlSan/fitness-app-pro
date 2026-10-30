from sqlalchemy import text

from app.database import engine

# create_all no modifica tablas existentes: las columnas nuevas se agregan a mano.
# Es seguro correrlo más de una vez (IF NOT EXISTS) y conserva los datos.
SENTENCIAS = [
    "ALTER TABLE perfiles_usuario ADD COLUMN IF NOT EXISTS ml_vaso INTEGER NOT NULL DEFAULT 250",
    "ALTER TABLE perfiles_usuario ADD COLUMN IF NOT EXISTS meta_hidratacion_ml INTEGER NOT NULL DEFAULT 2000",
]


def main():
    with engine.begin() as conexion:
        for sentencia in SENTENCIAS:
            conexion.execute(text(sentencia))
    print("Migración de la Etapa 8 aplicada.")


if __name__ == "__main__":
    main()