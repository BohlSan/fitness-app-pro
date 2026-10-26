import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.registry import mapper_registry


class EstadoEntrenamiento(str, enum.Enum):
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"


@mapper_registry.mapped
class Entrenamiento:
    __tablename__ = "entrenamientos"
    __table_args__ = (
        # Una persona no puede tener dos entrenamientos en curso a la vez
        Index(
            "uq_entrenamiento_en_curso_por_usuario",
            "usuario_id",
            unique=True,
            postgresql_where=text("estado = 'EN_CURSO'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), index=True
    )
    # RF-10: si la rutina se elimina, el entrenamiento permanece
    rutina_id: Mapped[int | None] = mapped_column(
        ForeignKey("rutinas.id", ondelete="SET NULL"), index=True, default=None
    )
    # Copia del nombre al momento de entrenar ("Fuerza · Pecho" o "Estilo libre")
    titulo: Mapped[str] = mapped_column(String(220))
    estado: Mapped[EstadoEntrenamiento] = mapped_column(
        Enum(EstadoEntrenamiento, native_enum=False, length=15)
    )
    fecha: Mapped[date] = mapped_column(Date, index=True)  # día local (Argentina)
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finalizado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    duracion_segundos: Mapped[int | None] = mapped_column(default=None)
    dificultad: Mapped[int | None] = mapped_column(default=None)  # 1 a 5
    cansancio: Mapped[int | None] = mapped_column(default=None)  # 1 a 5
    animo: Mapped[int | None] = mapped_column(default=None)  # 1 a 5
    agua_ml: Mapped[int | None] = mapped_column(default=None)

    ejercicios: Mapped[list["EjercicioEntrenamiento"]] = relationship(
        cascade="all, delete-orphan", order_by="EjercicioEntrenamiento.orden"
    )


@mapper_registry.mapped
class EjercicioEntrenamiento:
    __tablename__ = "ejercicios_entrenamiento"

    id: Mapped[int] = mapped_column(primary_key=True)
    entrenamiento_id: Mapped[int] = mapped_column(
        ForeignKey("entrenamientos.id", ondelete="CASCADE"), index=True
    )
    # RESTRICT: un ejercicio con historial no puede eliminarse
    ejercicio_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios.id", ondelete="RESTRICT"), index=True
    )
    orden: Mapped[int] = mapped_column(default=0)
    notas: Mapped[str | None] = mapped_column(String(500), default=None)

    series: Mapped[list["Serie"]] = relationship(
        cascade="all, delete-orphan", order_by="Serie.numero"
    )
    ejercicio: Mapped["Ejercicio"] = relationship()


@mapper_registry.mapped
class Serie:
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(primary_key=True)
    ejercicio_entrenamiento_id: Mapped[int] = mapped_column(
        ForeignKey("ejercicios_entrenamiento.id", ondelete="CASCADE"), index=True
    )
    numero: Mapped[int] = mapped_column()
    peso_kg: Mapped[float | None] = mapped_column(Float, default=None)
    repeticiones: Mapped[int] = mapped_column()
    completada: Mapped[bool] = mapped_column(default=False)