from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.models.ejercicio import GrupoMuscular, TipoMedicion


def _limpiar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class EjercicioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    grupo_principal: GrupoMuscular
    grupo_secundario: GrupoMuscular | None = None
    tipo_medicion: TipoMedicion = TipoMedicion.REPETICIONES
    usa_peso_corporal: bool = False

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
        return _limpiar_texto(valor)

    @model_validator(mode="after")
    def grupos_distintos(self):
        if self.grupo_secundario is not None and self.grupo_secundario == self.grupo_principal:
            raise ValueError("El grupo secundario debe ser distinto del principal")
        if self.usa_peso_corporal and self.tipo_medicion == TipoMedicion.TIEMPO:
            raise ValueError("El peso corporal solo se puede usar en ejercicios por repeticiones")
        return self



class EjercicioUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    descripcion: str | None = Field(default=None, max_length=500)
    grupo_principal: GrupoMuscular | None = None
    grupo_secundario: GrupoMuscular | None = None
    tipo_medicion: TipoMedicion | None = None
    usa_peso_corporal: bool | None = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str | None) -> str | None:
        if valor is None:
            return valor
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede estar vacío")
        return valor

    @field_validator("descripcion")
    @classmethod
    def limpiar_descripcion(cls, valor: str | None) -> str | None:
        return _limpiar_texto(valor)


class EjercicioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    grupo_principal: GrupoMuscular
    grupo_secundario: GrupoMuscular | None
    tipo_medicion: TipoMedicion
    usa_peso_corporal: bool
    creador_id: int | None

    @computed_field
    @property
    def es_base(self) -> bool:
        return self.creador_id is None


class GrupoOut(BaseModel):
    valor: str
    etiqueta: str