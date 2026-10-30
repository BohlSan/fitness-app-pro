from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.registry import mapper_registry


@mapper_registry.mapped
class RegistroHidratacion:
    """Una toma de agua. El total del día es la suma de sus registros (RF-27)."""

    __tablename__ = "registros_hidratacion"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    fecha: Mapped[date] = mapped_column(Date, index=True)
    cantidad_ml: Mapped[int] = mapped_column()
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )