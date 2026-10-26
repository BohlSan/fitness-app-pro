import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.registry import mapper_registry


class GrupoMuscular(str, enum.Enum):
    PECHO = "PECHO"
    ESPALDA = "ESPALDA"
    HOMBROS = "HOMBROS"
    BICEPS = "BICEPS"
    TRICEPS = "TRICEPS"
    ABDOMINALES = "ABDOMINALES"
    CUADRICEPS = "CUADRICEPS"
    ISQUIOTIBIALES = "ISQUIOTIBIALES"
    GLUTEOS = "GLUTEOS"
    PANTORRILLAS = "PANTORRILLAS"
    CUERPO_COMPLETO = "CUERPO_COMPLETO"
    CARDIO = "CARDIO"


ETIQUETAS_GRUPO_MUSCULAR = {
    GrupoMuscular.PECHO: "Pecho",
    GrupoMuscular.ESPALDA: "Espalda",
    GrupoMuscular.HOMBROS: "Hombros",
    GrupoMuscular.BICEPS: "Bíceps",
    GrupoMuscular.TRICEPS: "Tríceps",
    GrupoMuscular.ABDOMINALES: "Abdominales",
    GrupoMuscular.CUADRICEPS: "Cuádriceps",
    GrupoMuscular.ISQUIOTIBIALES: "Isquiotibiales",
    GrupoMuscular.GLUTEOS: "Glúteos",
    GrupoMuscular.PANTORRILLAS: "Pantorrillas",
    GrupoMuscular.CUERPO_COMPLETO: "Cuerpo completo",
    GrupoMuscular.CARDIO: "Cardio",
}


@mapper_registry.mapped
class Ejercicio:
    __tablename__ = "ejercicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), index=True)
    descripcion: Mapped[str | None] = mapped_column(String(500), default=None)
    grupo_principal: Mapped[GrupoMuscular] = mapped_column(
        Enum(GrupoMuscular, native_enum=False, length=30), index=True
    )
    grupo_secundario: Mapped[GrupoMuscular | None] = mapped_column(
        Enum(GrupoMuscular, native_enum=False, length=30), default=None
    )
    # NULL = ejercicio del catálogo base (solo lectura). Con valor = ejercicio propio
    creador_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id", ondelete="SET NULL"), index=True, default=None
    )