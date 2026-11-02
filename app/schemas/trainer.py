from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.perfil import ObjetivoFisico
from app.models.trainer import EstadoAsignacion, EstadoCuota, EstadoVinculo


# ---------- Entrada ----------
class VinculoIn(BaseModel):
    codigo: str = Field(min_length=4, max_length=12)


class CuotaIn(BaseModel):
    estado_cuota: EstadoCuota


class PagoIn(BaseModel):
    monto: int = Field(ge=1, le=100_000_000)
    fecha: date | None = Field(default=None, ge=date(2000, 1, 1))  # sin fecha: hoy
    concepto: str | None = Field(default=None, max_length=100)

    @field_validator("concepto")
    @classmethod
    def limpiar_concepto(cls, valor: str | None) -> str | None:
        if valor is None:
            return None
        return valor.strip() or None


class AsignacionIn(BaseModel):
    rutina_id: int


# ---------- Salida ----------
class CodigoOut(BaseModel):
    codigo_enlace: str


class PersonaOut(BaseModel):
    id: int
    nombre: str
    email: str


class PanelOut(BaseModel):
    nombre: str
    codigo_enlace: str
    clientes_activos: int
    solicitudes_pendientes: int
    actividad_sin_leer: int


class ClienteResumenOut(BaseModel):
    vinculo_id: int
    estado: EstadoVinculo
    estado_cuota: EstadoCuota
    inicio: date | None
    solicitado_en: datetime
    cliente: PersonaOut
    objetivo: ObjetivoFisico | None
    ultimo_entrenamiento: date | None
    dias_sin_entrenar: int | None


class ClienteDetalleOut(BaseModel):
    vinculo_id: int
    estado: EstadoVinculo
    estado_cuota: EstadoCuota
    inicio: date | None
    id: int
    nombre: str
    email: str
    edad: int | None
    altura_cm: int | None
    peso_actual_kg: float | None
    objetivo: ObjetivoFisico | None
    dias_entrenamiento_semana: int | None


class PagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha: date
    monto: int
    concepto: str | None


class AsignacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rutina_id: int | None
    rutina_nombre: str
    fecha_asignacion: date
    estado: EstadoAsignacion


class ActividadOut(BaseModel):
    id: int
    cliente: PersonaOut
    tipo: str
    entrenamiento_id: int | None
    titulo: str
    fecha: date
    duracion_segundos: int | None
    volumen_kg: float
    creada_en: datetime
    leida: bool


class EntrenadorOut(BaseModel):
    id: int
    nombre: str


class MiVinculoOut(BaseModel):
    """La relación vista por el cliente."""

    vinculo_id: int
    estado: EstadoVinculo
    estado_cuota: EstadoCuota
    inicio: date | None
    trainer: EntrenadorOut
    pagos: list[PagoOut]