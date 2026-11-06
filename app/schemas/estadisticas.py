from datetime import date

from pydantic import BaseModel, Field

from app.models.ejercicio import GrupoMuscular, TipoMedicion


# ---------- Peso corporal ----------
class PesoIn(BaseModel):
    fecha: date | None = Field(default=None, ge=date(2000, 1, 1))  # sin fecha: hoy
    peso_kg: float = Field(gt=20, le=400)


class RegistroPesoOut(BaseModel):
    id: int
    fecha: date
    peso_kg: float


class PuntoPesoOut(BaseModel):
    fecha: date
    peso_kg: float


class TendenciaPesoOut(BaseModel):
    pendiente_kg_semana: float
    direccion: str  # BAJA, SUBE o ESTABLE
    puntos: list[PuntoPesoOut]  # un punto de la recta por cada registro


class EvolucionPesoOut(BaseModel):
    registros: list[RegistroPesoOut]
    peso_inicial: float | None
    peso_actual: float | None
    variacion_kg: float | None
    tendencia: TendenciaPesoOut | None


# ---------- Resumen ----------
class SemanaOut(BaseModel):
    semana_inicio: date
    cantidad: int


class ResumenOut(BaseModel):
    cantidad_entrenamientos: int
    frecuencia_semanal: float
    duracion_promedio_segundos: float | None
    volumen_total_kg: float
    agua_promedio_ml: float | None
    por_semana: list[SemanaOut]


# ---------- Ejercicios ----------
class MarcaPesoOut(BaseModel):
    peso_kg: float
    repeticiones: int
    fecha: date
    entrenamiento_id: int


class MarcaVolumenOut(BaseModel):
    volumen_kg: float
    fecha: date
    entrenamiento_id: int


class RepeticionesPesoOut(BaseModel):
    peso_kg: float
    repeticiones: int
    fecha: date


class MarcaDuracionOut(BaseModel):
    duracion_segundos: int
    fecha: date
    entrenamiento_id: int


class MarcasOut(BaseModel):
    mayor_peso: MarcaPesoOut | None
    mayor_duracion: MarcaDuracionOut | None
    mejor_volumen_sesion: MarcaVolumenOut | None
    repeticiones_por_peso: list[RepeticionesPesoOut]


class SesionEjercicioOut(BaseModel):
    entrenamiento_id: int
    fecha: date
    volumen_kg: float
    peso_max_kg: float
    series: int
    repeticiones: int
    duracion_total_segundos: int


class EvolucionEjercicioOut(BaseModel):
    ejercicio_id: int
    nombre: str
    grupo_principal: GrupoMuscular
    tipo_medicion: TipoMedicion
    usa_peso_corporal: bool
    volumen_total_kg: float
    duracion_total_segundos: int
    sesiones: list[SesionEjercicioOut]
    marcas: MarcasOut


class EjercicioEntrenadoOut(BaseModel):
    ejercicio_id: int
    nombre: str
    grupo_principal: GrupoMuscular
    tipo_medicion: TipoMedicion
    usa_peso_corporal: bool
    sesiones: int
    ultima_fecha: date
    mayor_peso_kg: float | None
    mejor_volumen_sesion_kg: float | None
    mayor_duracion_segundos: int | None


class PROut(BaseModel):
    ejercicio_id: int
    nombre: str
    tipo: str  # PESO, VOLUMEN, REPETICIONES o DURACION
    valor: float
    anterior: float
    peso_kg: float | None = None  # solo para REPETICIONES