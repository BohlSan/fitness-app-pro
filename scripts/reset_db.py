import app.models  # noqa: F401
from app.database import engine
from app.db.registry import metadata


def main():
    respuesta = input(
        "Esto BORRA todas las tablas de DATABASE_URL (base compartida del equipo).\n"
        "Escribí RESETEAR para continuar: "
    )
    if respuesta != "RESETEAR":
        print("Cancelado.")
        return
    metadata.drop_all(bind=engine)
    metadata.create_all(bind=engine)
    print("Base recreada.")


if __name__ == "__main__":
    main()