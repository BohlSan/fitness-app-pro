from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# Engine: se conecta con la base de datos (PostgreSQL en Supabase)
engine = create_engine(settings.database_url, pool_pre_ping=True)

# Session: la ORM la provee a partir del Engine
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
