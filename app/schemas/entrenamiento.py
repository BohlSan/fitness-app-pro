from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.models.entrenamiento import EstadoEntrenamiento
from app.schemas.ejercicio import EjercicioOut
from app.services.calculos import volumen_series


# ---------- Entrada ----------
class EntrenamientoStart(BaseModel):
    rutina_id: int | None = None
    dia_id: int | None = None

    @model_validator(mode="after")
    def rutina_y_dia_juntos(self):
        if (self.rutina_id is None) != (self.dia_id is None):
            raise ValueError("Indicá la rutina y el día, o ninguno para entrenar en estilo libre")
        return self


class SerieIn(BaseModel):
    id: int | None = None  # con id: se actualiza; sin id: se crea
    peso_kg: float | None = Field(default=None, ge=0, le=1000)
    repeticiones: int = Field(ge=1, le=200)
    completada: bool = False


class EjercicioEntrenamientoIn(BaseModel):
    id: int | None = None
    ejercicio_id: int
    notas: str | None = Field(default=None, max_length=500)
    series: list[SerieIn] = Field(default_factory=list, max_length=30)

    @field_validator("notas")
    @classmethod
    def limpiar_notas(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class EntrenamientoSync(BaseModel):
    ejercicios: list[EjercicioEntrenamientoIn] = Field(default_factory=list, max_length=40)


class FinalizarIn(BaseModel):
    agua_ml: int | None = Field(default=None, ge=0, le=10000)
    dificultad: int | None = Field(default=None, ge=1, le=5)
    cansancio: int | None = Field(default=None, ge=1, le=5)
    animo: int | None = Field(default=None, ge=1, le=5)


# ---------- Salida ----------
class SerieOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: int
    peso_kg: float | None
    repeticiones: int
    completada: bool


class EjercicioEntrenamientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    orden: int
    notas: str | None
    ejercicio: EjercicioOut
    series: list[SerieOut]

    @computed_field
    @property
    def volumen_kg(self) -> float:
        return round(volumen_series(self.series), 2)


class EntrenamientoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    rutina_id: int | None
    estado: EstadoEntrenamiento
    fecha: date
    iniciado_en: datetime
    finalizado_en: datetime | None
    duracion_segundos: int | None
    dificultad: int | None
    cansancio: int | None
    animo: int | None
    agua_ml: int | None
    ejercicios: list[EjercicioEntrenamientoOut]

    @computed_field
    @property
    def volumen_total_kg(self) -> float:
        return round(sum(volumen_series(e.series) for e in self.ejercicios), 2)

    @computed_field
    @property
    def series_completadas(self) -> int:
        return sum(1 for e in self.ejercicios for s in e.series if s.completada)