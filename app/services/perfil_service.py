from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.perfil import PerfilUsuario, RegistroPeso, UnidadHidratacion
from app.models.usuario import Usuario
from app.schemas.perfil import PerfilCreate, PerfilUpdate
from app.services.fechas import hoy


class PerfilYaExiste(Exception):
    pass


class PerfilNoEncontrado(Exception):
    pass


class DatosPerfilInvalidos(Exception):
    pass


def obtener_perfil(db: Session, usuario_id: int) -> PerfilUsuario | None:
    return db.get(PerfilUsuario, usuario_id)


def guardar_peso_del_dia(
    db: Session, usuario_id: int, peso_kg: float, fecha: date | None = None
) -> RegistroPeso:
    """Crea el registro de peso del día o actualiza el existente. No hace commit."""
    fecha = fecha or hoy()
    registro = db.scalar(
        select(RegistroPeso).where(
            RegistroPeso.usuario_id == usuario_id, RegistroPeso.fecha == fecha
        )
    )
    if registro is None:
        registro = RegistroPeso(usuario_id=usuario_id, fecha=fecha, peso_kg=peso_kg)
        db.add(registro)
    else:
        registro.peso_kg = peso_kg
    return registro


def _normalizar_hidratacion(perfil: PerfilUsuario) -> None:
    if perfil.unidad_hidratacion == UnidadHidratacion.BOTELLAS:
        if perfil.ml_botella is None:
            raise DatosPerfilInvalidos("Indicá cuántos ml tiene tu botella")
    else:
        perfil.ml_botella = None


def crear_perfil(db: Session, usuario: Usuario, datos: PerfilCreate) -> PerfilUsuario:
    if db.get(PerfilUsuario, usuario.id) is not None:
        raise PerfilYaExiste()

    perfil = PerfilUsuario(usuario_id=usuario.id, **datos.model_dump())
    _normalizar_hidratacion(perfil)
    db.add(perfil)
    guardar_peso_del_dia(db, usuario.id, perfil.peso_actual_kg)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise PerfilYaExiste()
    db.refresh(perfil)
    return perfil


def actualizar_perfil(
    db: Session, usuario: Usuario, cambios: PerfilUpdate
) -> PerfilUsuario:
    perfil = db.get(PerfilUsuario, usuario.id)
    if perfil is None:
        raise PerfilNoEncontrado()

    datos = {
        campo: valor
        for campo, valor in cambios.model_dump(exclude_unset=True).items()
        if valor is not None
    }
    for campo, valor in datos.items():
        setattr(perfil, campo, valor)

    try:
        _normalizar_hidratacion(perfil)
    except DatosPerfilInvalidos:
        db.rollback()
        raise

    if "peso_actual_kg" in datos:
        guardar_peso_del_dia(db, usuario.id, perfil.peso_actual_kg)

    db.commit()
    db.refresh(perfil)
    return perfil