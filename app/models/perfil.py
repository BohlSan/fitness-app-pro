import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.registry import mapper_registry


class Genero(str, enum.Enum):
    MASCULINO = "MASCULINO"
    FEMENINO = "FEMENINO"
    OTRO = "OTRO"


class ObjetivoFisico(str, enum.Enum):
    PERDER_PESO = "PERDER_PESO"
    GANAR_MASA_MUSCULAR = "GANAR_MASA_MUSCULAR"
    MANTENER_PESO = "MANTENER_PESO"
    MEJORAR_RENDIMIENTO = "MEJORAR_RENDIMIENTO"


class UnidadHidratacion(str, enum.Enum):
    ML = "ML"
    BOTELLAS = "BOTELLAS"


@mapper_registry.mapped
class PerfilUsuario:
    __tablename__ = "perfiles_usuario"

    # Relación 1 a 1 con Usuario. Si se borra el usuario, se borra su perfil (RNF-03)
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    )
    fecha_nacimiento: Mapped[date] = mapped_column(Date)
    genero: Mapped[Genero] = mapped_column(Enum(Genero, native_enum=False, length=20))
    altura_cm: Mapped[int] = mapped_column()
    peso_actual_kg: Mapped[float] = mapped_column(Float)
    objetivo: Mapped[ObjetivoFisico] = mapped_column(
        Enum(ObjetivoFisico, native_enum=False, length=30)
    )
    dias_entrenamiento_semana: Mapped[int] = mapped_column()
    unidad_hidratacion: Mapped[UnidadHidratacion] = mapped_column(
        Enum(UnidadHidratacion, native_enum=False, length=20)
    )
    ml_botella: Mapped[int | None] = mapped_column(default=None)


@mapper_registry.mapped
class RegistroPeso:
    __tablename__ = "registros_peso"
    __table_args__ = (
        # Un solo registro de peso por usuario y por día
        UniqueConstraint("usuario_id", "fecha", name="uq_registro_peso_usuario_fecha"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    fecha: Mapped[date] = mapped_column(Date)
    peso_kg: Mapped[float] = mapped_column(Float)