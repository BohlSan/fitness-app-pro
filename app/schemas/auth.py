from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.usuario import RolUsuario


class RegistroIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    rol: RolUsuario

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("El nombre no puede estar vacío")
        return valor

    @field_validator("password")
    @classmethod
    def password_dentro_del_limite_de_bcrypt(cls, valor: str) -> str:
        if len(valor.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga")
        return valor


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    email: str
    rol: RolUsuario


class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut