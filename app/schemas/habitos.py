from datetime import date

from pydantic import BaseModel, Field

from app.models.perfil import UnidadHidratacion


# ---------- Racha ----------
class RachaOut(BaseModel):
    racha_actual: int
    racha_maxima: int
    meta_semanal: int
    dias_esta_semana: int
    faltan_esta_semana: int
    cumplida_esta_semana: bool
    en_riesgo: bool


# ---------- Hidratación ----------
class HidratacionIn(BaseModel):
    cantidad_ml: int = Field(ge=10, le=3000)
    fecha: date | None = Field(default=None, ge=date(2000, 1, 1))  # sin fecha: hoy


class RegistroHidratacionOut(BaseModel):
    id: int
    cantidad_ml: int


class HidratacionDiaOut(BaseModel):
    fecha: date
    meta_ml: int
    bebido_ml: int  # lo que se registró durante el día
    entrenamiento_ml: int  # lo que se tomó entrenando (se suma automáticamente)
    total_ml: int
    porcentaje: int
    cumplida: bool
    unidad: UnidadHidratacion
    ml_vaso: int
    ml_botella: int | None
    registros: list[RegistroHidratacionOut]


class DiaHidratacionOut(BaseModel):
    fecha: date
    bebido_ml: int
    entrenamiento_ml: int
    total_ml: int
    meta_ml: int
    cumplio: bool