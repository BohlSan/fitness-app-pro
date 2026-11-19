import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registra los modelos en la metadata)
from app.config import settings
from app.database import get_db
from app.db.registry import metadata
from app.main import app


@pytest.fixture(scope="session")
def engine():
    if not settings.test_database_url:
        pytest.exit("Falta TEST_DATABASE_URL en el .env", returncode=1)
    if settings.test_database_url == settings.database_url:
        pytest.exit(
            "TEST_DATABASE_URL no puede ser igual a DATABASE_URL: "
            "los tests borran las tablas.",
            returncode=1,
        )
    test_engine = create_engine(settings.test_database_url, pool_pre_ping=True)
    metadata.drop_all(test_engine)
    metadata.create_all(test_engine)
    yield test_engine
    metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture()
def db(engine):
    # Cada test corre dentro de una transacción que se revierte al terminar
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _crear_cuenta(client, email, rol):
    respuesta = client.post(
        "/auth/registro",
        json={"nombre": "Test", "email": email, "password": "secreta123", "rol": rol},
    )
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.fixture()
def headers_usuario(client):
    return _crear_cuenta(client, "usuario@example.com", "USUARIO")


@pytest.fixture()
def headers_trainer(client):
    return _crear_cuenta(client, "trainer@example.com", "PERSONAL_TRAINER")


@pytest.fixture()
def headers_otro_usuario(client):
    return _crear_cuenta(client, "otro@example.com", "USUARIO")


@pytest.fixture()
def ejercicios(db):
    """Tres ejercicios del catálogo. Devuelve sus ids."""
    from app.models.ejercicio import GrupoMuscular
    from app.schemas.ejercicio import EjercicioCreate
    from app.services.ejercicio_factory import EjercicioFactory

    ids = []
    for nombre, grupo in [
        ("Press de banca", GrupoMuscular.PECHO),
        ("Aperturas", GrupoMuscular.PECHO),
        ("Dominadas", GrupoMuscular.ESPALDA),
    ]:
        ejercicio = EjercicioFactory.crear_base(
            EjercicioCreate(nombre=nombre, grupo_principal=grupo)
        )
        db.add(ejercicio)
        db.commit()
        ids.append(ejercicio.id)
    return ids


@pytest.fixture()
def entrenar(client, db):
    """Hace un entrenamiento completo en la fecha indicada y devuelve su id."""
    from datetime import datetime, time, timezone

    from app.models.entrenamiento import Entrenamiento

    def _entrenar(headers, ejercicio_id, fecha, series=((60, 10),), agua_ml=None):
        creado = client.post("/entrenamientos", json={}, headers=headers).json()
        url = f"/entrenamientos/{creado['id']}"
        client.put(
            url,
            json={
                "ejercicios": [
                    {
                        "ejercicio_id": ejercicio_id,
                        "series": [
                            {"peso_kg": peso, "repeticiones": reps, "completada": True}
                            for peso, reps in series
                        ],
                    }
                ]
            },
            headers=headers,
        )
        client.post(f"{url}/finalizar", json={"agua_ml": agua_ml}, headers=headers)

        registro = db.get(Entrenamiento, creado["id"])
        registro.fecha = fecha
        registro.iniciado_en = datetime.combine(fecha, time(10, 0), tzinfo=timezone.utc)
        db.commit()
        return creado["id"]

    return _entrenar


@pytest.fixture()
def headers_otro_trainer(client):
    return _crear_cuenta(client, "trainer2@example.com", "PERSONAL_TRAINER")
