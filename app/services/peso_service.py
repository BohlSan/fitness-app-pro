from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.perfil import PerfilUsuario, RegistroPeso
from app.models.usuario import Usuario
from app.services import calculos
from app.services.fechas import hoy
from app.services.perfil_service import guardar_peso_del_dia


class PerfilIncompleto(Exception):
    pass


class DatosPesoInvalidos(Exception):
    pass


def registrar_peso(
    db: Session, usuario: Usuario, peso_kg: float, fecha: date | None = None
) -> None:
    """Un registro por día: otro día se suma, el mismo día se corrige (RF-21)."""
    fecha = fecha or hoy()
    if fecha > hoy():
        raise DatosPesoInvalidos("La fecha no puede ser futura")

    perfil = db.get(PerfilUsuario, usuario.id)
    if perfil is None:
        raise PerfilIncompleto()

    guardar_peso_del_dia(db, usuario.id, peso_kg, fecha)
    db.flush()

    # El peso actual del perfil siempre es el del registro más reciente
    ultimo = db.scalar(
        select(RegistroPeso)
        .where(RegistroPeso.usuario_id == usuario.id)
        .order_by(RegistroPeso.fecha.desc())
        .limit(1)
    )
    perfil.peso_actual_kg = ultimo.peso_kg
    db.commit()


def obtener_evolucion(
    db: Session, usuario_id: int, desde: date | None = None, hasta: date | None = None
) -> dict:
    consulta = select(RegistroPeso).where(RegistroPeso.usuario_id == usuario_id)
    if desde is not None:
        consulta = consulta.where(RegistroPeso.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(RegistroPeso.fecha <= hasta)
    registros = list(db.scalars(consulta.order_by(RegistroPeso.fecha)))

    inicial = registros[0].peso_kg if registros else None
    actual = registros[-1].peso_kg if registros else None
    return {
        "registros": [{"id": r.id, "fecha": r.fecha, "peso_kg": r.peso_kg} for r in registros],
        "peso_inicial": inicial,
        "peso_actual": actual,
        "variacion_kg": round(actual - inicial, 2) if registros else None,
        "tendencia": calculos.calcular_tendencia([(r.fecha, r.peso_kg) for r in registros]),
    }