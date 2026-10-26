from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.registry import mapper_registry


@mapper_registry.mapped
class RegistroAuditoria:
    """RNF-16: quién hizo qué y cuándo."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), index=True, default=None
    )
    accion: Mapped[str] = mapped_column(String(50))
    entidad: Mapped[str] = mapped_column(String(50))
    # Sin clave foránea: tiene que sobrevivir al borrado de la entidad
    entidad_id: Mapped[int | None] = mapped_column(default=None)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )