import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.registry import mapper_registry


class RolUsuario(str, enum.Enum):
    USUARIO = "USUARIO"
    PERSONAL_TRAINER = "PERSONAL_TRAINER"


@mapper_registry.mapped
class Usuario:
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # native_enum=False: se guarda como texto, así sumar roles nuevos (RNF-06)
    # no requiere modificar un tipo enum de PostgreSQL
    rol: Mapped[RolUsuario] = mapped_column(
        Enum(RolUsuario, native_enum=False, length=30)
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )