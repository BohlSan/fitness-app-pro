from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.perfil import Genero, ObjetivoFisico, UnidadHidratacion
from app.services.fechas import calcular_edad

EDAD_MINIMA = 14
EDAD_MAXIMA = 100


def _validar_fecha_nacimiento(valor: date | None) -> date | None:
    if valor is None:
        return valor
    edad = calcular_edad(valor)
    if edad < EDAD_MINIMA or edad > EDAD_MAXIMA:
        raise ValueError(f"La edad debe estar entre {EDAD_MINIMA} y {EDAD_MAXIMA} años")
    return valor


class PerfilCreate(BaseModel):
    fecha_nacimiento: date
    genero: Genero
    altura_cm: int = Field(ge=100, le=250)
    peso_actual_kg: float = Field(gt=20, le=400)
    objetivo: ObjetivoFisico
    dias_entrenamiento_semana: int = Field(ge=1, le=7)
    unidad_hidratacion: UnidadHidratacion
    ml_botella: int | None = Field(default=None, ge=100, le=5000)

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha(cls, valor: date) -> date:
        return _validar_fecha_nacimiento(valor)


class PerfilUpdate(BaseModel):
    fecha_nacimiento: date | None = None
    genero: Genero | None = None
    altura_cm: int | None = Field(default=None, ge=100, le=250)
    peso_actual_kg: float | None = Field(default=None, gt=20, le=400)
    objetivo: ObjetivoFisico | None = None
    dias_entrenamiento_semana: int | None = Field(default=None, ge=1, le=7)
    unidad_hidratacion: UnidadHidratacion | None = None
    ml_botella: int | None = Field(default=None, ge=100, le=5000)

    @field_validator("fecha_nacimiento")
    @classmethod
    def validar_fecha(cls, valor: date | None) -> date | None:
        return _validar_fecha_nacimiento(valor)


class PerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha_nacimiento: date
    genero: Genero
    altura_cm: int
    peso_actual_kg: float
    objetivo: ObjetivoFisico
    dias_entrenamiento_semana: int
    unidad_hidratacion: UnidadHidratacion
    ml_botella: int | None

    @computed_field
    @property
    def edad(self) -> int:
        return calcular_edad(self.fecha_nacimiento)