import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.registry import mapper_registry


class EstadoVinculo(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    ACTIVA = "ACTIVA"
    FINALIZADA = "FINALIZADA"


class EstadoCuota(str, enum.Enum):
    AL_DIA = "AL_DIA"
    PENDIENTE = "PENDIENTE"
    VENCIDA = "VENCIDA"


class EstadoAsignacion(str, enum.Enum):
    ACTIVA = "ACTIVA"
    FINALIZADA = "FINALIZADA"


@mapper_registry.mapped
class PerfilTrainer:
    """Datos propios del trainer: por ahora, su código de enlace."""

    __tablename__ = "perfiles_trainer"

    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    codigo_enlace: Mapped[str] = mapped_column(String(12), unique=True, index=True)


@mapper_registry.mapped
class VinculoTrainer:
    """Relación entrenador-cliente (RF-13)."""

    __tablename__ = "vinculos_trainer"
    __table_args__ = (
        # Un cliente tiene como máximo una relación vigente (pendiente o activa)
        Index(
            "uq_vinculo_vivo_por_cliente",
            "cliente_id",
            unique=True,
            postgresql_where=text("estado IN ('PENDIENTE', 'ACTIVA')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    estado: Mapped[EstadoVinculo] = mapped_column(
        Enum(EstadoVinculo, native_enum=False, length=15)
    )
    estado_cuota: Mapped[EstadoCuota] = mapped_column(
        Enum(EstadoCuota, native_enum=False, length=15)
    )
    solicitado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    inicio: Mapped[date | None] = mapped_column(Date, default=None)  # al aceptarla
    fin: Mapped[date | None] = mapped_column(Date, default=None)


@mapper_registry.mapped
class PagoCliente:
    """Historial de pagos de una relación (RF-13)."""

    __tablename__ = "pagos_cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    vinculo_id: Mapped[int] = mapped_column(
        ForeignKey("vinculos_trainer.id", ondelete="CASCADE"), index=True
    )
    fecha: Mapped[date] = mapped_column(Date)
    monto: Mapped[int] = mapped_column()  # en pesos
    concepto: Mapped[str | None] = mapped_column(String(100), default=None)


@mapper_registry.mapped
class AsignacionRutina:
    """Rutina que un trainer asignó a un cliente (RF-11)."""

    __tablename__ = "asignaciones_rutina"

    id: Mapped[int] = mapped_column(primary_key=True)
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    # Si la rutina se elimina, la asignación queda como registro histórico
    rutina_id: Mapped[int | None] = mapped_column(
        ForeignKey("rutinas.id", ondelete="SET NULL"), index=True, default=None
    )
    rutina_nombre: Mapped[str] = mapped_column(String(100))
    fecha_asignacion: Mapped[date] = mapped_column(Date)
    estado: Mapped[EstadoAsignacion] = mapped_column(
        Enum(EstadoAsignacion, native_enum=False, length=15)
    )


@mapper_registry.mapped
class ActividadCliente:
    """Novedades del panel del trainer. Las genera el Observer."""

    __tablename__ = "actividad_cliente"

    id: Mapped[int] = mapped_column(primary_key=True)
    trainer_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    cliente_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(40))
    entrenamiento_id: Mapped[int | None] = mapped_column(
        ForeignKey("entrenamientos.id", ondelete="SET NULL"), default=None
    )
    titulo: Mapped[str] = mapped_column(String(220))
    fecha: Mapped[date] = mapped_column(Date)
    duracion_segundos: Mapped[int | None] = mapped_column(default=None)
    volumen_kg: Mapped[float] = mapped_column(default=0)
    creada_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    leida: Mapped[bool] = mapped_column(default=False)