from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class CuentaUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password_actual: str | None = Field(default=None, max_length=128)  # para cambiar el email

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str | None) -> str | None:
        if valor is None:
            return valor
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede estar vacío")
        return valor


class CambioPasswordIn(BaseModel):
    password_actual: str = Field(min_length=1, max_length=128)
    password_nueva: str = Field(min_length=8, max_length=72)

    @field_validator("password_nueva")
    @classmethod
    def dentro_del_limite_de_bcrypt(cls, valor: str) -> str:
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga")
        return valor


class EliminarCuentaIn(BaseModel):
    # Cualquier otro texto se rechaza con 422
    confirmacion: Literal["ELIMINAR"]