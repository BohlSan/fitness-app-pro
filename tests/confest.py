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
