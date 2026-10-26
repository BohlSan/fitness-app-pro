import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.registry import mapper_registry


class DiaSemana(str, enum.Enum):
    LUNES = "LUNES"
    MARTES = "MARTES"
    MIERCOLES = "MIERCOLES"
    JUEVES = "JUEVES"
    VIERNES = "VIERNES"
    SABADO = "SABADO"
    DOMINGO = "DOMINGO"


ORDEN_DIA_SEMANA = {dia: posicion for posicion, dia in enumerate(DiaSemana)}


@mapper_registry.mapped
class Rutina:
    __tablename__ = "rutinas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(String(500), default=None)
    # Quien la creó (usuario o trainer). Queda vacío si esa cuenta se elimina
    autor_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), index=True, default=None
    )
    # Quien la usa y puede modificarla
    propietario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    dias: Mapped[list["DiaRutina"]] = relationship(cascade="all, delete-orphan")


@mapper_registry.mapped
class DiaRutina:
    __tablename__ = "dias_rutina"

    id: Mapped[int] = mapped_column(primary_key=True)
    rutina_id: Mapped[int] = mapped_column(
        ForeignKey("rutinas.id", ondelete="CASCADE"), index=True
    )
    dia_semana: Mapped[DiaSemana] = mapped_column(
        Enum(DiaSemana, native_enum=False, length=15)
    )
    nombre: Mapped[str] = mapped_column(String(100))

    ejercicios: Mapped[list["RutinaEjercicio"]] = relationship(
        cascade="all, delete-orphan", order_by="RutinaEjercicio.orden"
    )


@mapper_registry.mapped
class RutinaEjercicio:
    __tablename__ = "rutina_ejercicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    dia_id: Mapped[int] = mapped_column(
        ForeignKey("dias_rutina.id", ondelete="CASCADE"), index=True
    )
    # RESTRICT: un ejercicio usado en una rutina no puede borrarse
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios.id", ondelete="RESTRICT"), index=True
    )
    orden: Mapped[int] = mapped_column(default=0)
    series: Mapped[int] = mapped_column()
    repeticiones: Mapped[int] = mapped_column()
    peso_sugerido_kg: Mapped[float | None] = mapped_column(Float, default=None)
    descanso_segundos: Mapped[int | None] = mapped_column(default=None)

    ejercicio: Mapped["Ejercicio"] = relationship()