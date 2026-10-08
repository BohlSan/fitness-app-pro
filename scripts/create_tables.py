import app.models  # noqa: F401  (registra los modelos en la metadata)
from app.database import engine
from app.db.registry import metadata


def main():
    metadata.create_all(bind=engine)
    print("Tablas creadas. Las que ya existían no se modifican.")


if __name__ == "__main__":
    main()