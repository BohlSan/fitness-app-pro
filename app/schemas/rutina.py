from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.rutina import ORDEN_DIA_SEMANA, DiaSemana
from app.schemas.ejercicio import EjercicioOut


# ---------- Entrada (crear y modificar) ----------
class EjercicioRutinaIn(BaseModel):
    id: int | None = None  # con id: se actualiza; sin id: se crea
    ejercicio_id: int
    series: int | None = Field(default=None, ge=1, le=20)
    repeticiones: int | None = Field(default=None, ge=1, le=100)
    duracion_sugerida_segundos: int | None = Field(default=None, ge=1, le=86400)
    peso_sugerido_kg: float | None = Field(default=None, ge=0, le=1000)
    descanso_segundos: int | None = Field(default=None, ge=0, le=3600)

    @model_validator(mode="after")
    def validar_tipo_de_registro(self):
        es_tiempo = self.duracion_sugerida_segundos is not None
        if es_tiempo and (self.series is not None or self.repeticiones is not None):
            raise ValueError("Un ejercicio por tiempo no lleva series ni repeticiones")
        if es_tiempo and (self.peso_sugerido_kg is not None or self.descanso_segundos is not None):
            raise ValueError("Un ejercicio por tiempo no lleva peso ni descanso por serie")
        if not es_tiempo and (self.series is None or self.repeticiones is None):
            raise ValueError("Indicá series y repeticiones para ejercicios de fuerza")
        return self


class DiaRutinaIn(BaseModel):
    id: int | None = None
    dia_semana: DiaSemana
    nombre: str = Field(min_length=1, max_length=100)
    ejercicios: list[EjercicioRutinaIn] = Field(default_factory=list, max_length=40)

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre del entrenamiento no puede estar vacío")
        return valor


class RutinaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    dias: list[DiaRutinaIn] = Field(min_length=1, max_length=7)

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede estar vacío")
        return valor

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None

    @model_validator(mode="after")
    def dias_sin_repetir(self):
        dias = [dia.dia_semana for dia in self.dias]
        if len(set(dias)) != len(dias):
            raise ValueError("No puede haber dos entrenamientos el mismo día de la semana")
        return self


# ---------- Salida ----------
class EjercicioRutinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden: int
    series: int | None
    repeticiones: int | None
    duracion_sugerida_segundos: int | None
    peso_sugerido_kg: float | None
    descanso_segundos: int | None
    ejercicio: EjercicioOut


class DiaRutinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dia_semana: DiaSemana
    nombre: str
    ejercicios: list[EjercicioRutinaOut]


class RutinaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    autor_id: int | None
    propietario_id: int
    creado_en: datetime
    dias: list[DiaRutinaOut]

    @field_validator("dias")
    @classmethod
    def ordenar_dias(cls, dias: list[DiaRutinaOut]) -> list[DiaRutinaOut]:
        # Siempre de lunes a domingo, sin importar el orden en que se cargaron
        return sorted(dias, key=lambda dia: ORDEN_DIA_SEMANA[dia.dia_semana])