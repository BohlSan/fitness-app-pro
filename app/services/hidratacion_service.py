from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entrenamiento import Entrenamiento, EstadoEntrenamiento
from app.models.hidratacion import RegistroHidratacion
from app.models.perfil import PerfilUsuario
from app.services.fechas import hoy
from app.services.peso_service import PerfilIncompleto  # noqa: F401  (se reutiliza)


class RegistroNoEncontrado(Exception):
    pass


class FechaInvalida(Exception):
    pass


def _perfil(db: Session, usuario_id: int) -> PerfilUsuario:
    perfil = db.get(PerfilUsuario, usuario_id)
    if perfil is None:
        raise PerfilIncompleto()
    return perfil


def _agua_registrada(db: Session, usuario_id: int, desde: date, hasta: date) -> dict[date, int]:
    filas = db.execute(
        select(RegistroHidratacion.fecha, func.sum(RegistroHidratacion.cantidad_ml))
        .where(
            RegistroHidratacion.usuario_id == usuario_id,
            RegistroHidratacion.fecha >= desde,
            RegistroHidratacion.fecha <= hasta,
        )
        .group_by(RegistroHidratacion.fecha)
    ).all()
    return {fecha: int(total) for fecha, total in filas}


def _agua_de_entrenamientos(db: Session, usuario_id: int, desde: date, hasta: date) -> dict[date, int]:
    """El agua que se toma entrenando también cuenta para el total del día."""
    filas = db.execute(
        select(Entrenamiento.fecha, func.coalesce(func.sum(Entrenamiento.agua_ml), 0))
        .where(
            Entrenamiento.usuario_id == usuario_id,
            Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
            Entrenamiento.fecha >= desde,
            Entrenamiento.fecha <= hasta,
        )
        .group_by(Entrenamiento.fecha)
    ).all()
    return {fecha: int(total) for fecha, total in filas}


def obtener_dia(db: Session, usuario_id: int, fecha: date | None = None) -> dict:
    fecha = fecha or hoy()
    perfil = _perfil(db, usuario_id)

    registros = list(
        db.scalars(
            select(RegistroHidratacion)
            .where(
                RegistroHidratacion.usuario_id == usuario_id,
                RegistroHidratacion.fecha == fecha,
            )
            .order_by(RegistroHidratacion.id)
        )
    )
    bebido = sum(registro.cantidad_ml for registro in registros)
    entrenamiento = _agua_de_entrenamientos(db, usuario_id, fecha, fecha).get(fecha, 0)
    total = bebido + entrenamiento
    meta = perfil.meta_hidratacion_ml

    return {
        "fecha": fecha,
        "meta_ml": meta,
        "bebido_ml": bebido,
        "entrenamiento_ml": entrenamiento,
        "total_ml": total,
        "porcentaje": round(total * 100 / meta),
        "cumplida": total >= meta,
        "unidad": perfil.unidad_hidratacion,
        "ml_vaso": perfil.ml_vaso,
        "ml_botella": perfil.ml_botella,
        "registros": [{"id": r.id, "cantidad_ml": r.cantidad_ml} for r in registros],
    }


def registrar(db: Session, usuario_id: int, cantidad_ml: int, fecha: date | None = None) -> None:
    fecha = fecha or hoy()
    if fecha > hoy():
        raise FechaInvalida("La fecha no puede ser futura")
    _perfil(db, usuario_id)

    db.add(RegistroHidratacion(usuario_id=usuario_id, fecha=fecha, cantidad_ml=cantidad_ml))
    db.commit()


def eliminar(db: Session, usuario_id: int, registro_id: int) -> date:
    """Elimina una toma (deshacer). Devuelve la fecha para mostrar el día actualizado."""
    registro = db.get(RegistroHidratacion, registro_id)
    # La toma de otra persona se trata como inexistente (RNF-15)
    if registro is None or registro.usuario_id != usuario_id:
        raise RegistroNoEncontrado()
    fecha = registro.fecha
    db.delete(registro)
    db.commit()
    return fecha


def historial(db: Session, usuario_id: int, dias: int) -> list[dict]:
    """Total diario de los últimos `dias` días (con ceros), contra la meta actual."""
    perfil = _perfil(db, usuario_id)
    fin = hoy()
    inicio = fin - timedelta(days=dias - 1)
    registrada = _agua_registrada(db, usuario_id, inicio, fin)
    entrenando = _agua_de_entrenamientos(db, usuario_id, inicio, fin)

    resultado = []
    for desplazamiento in range(dias):
        dia = inicio + timedelta(days=desplazamiento)
        bebido = registrada.get(dia, 0)
        en_entrenamiento = entrenando.get(dia, 0)
        total = bebido + en_entrenamiento
        resultado.append(
            {
                "fecha": dia,
                "bebido_ml": bebido,
                "entrenamiento_ml": en_entrenamiento,
                "total_ml": total,
                "meta_ml": perfil.meta_hidratacion_ml,
                "cumplio": total >= perfil.meta_hidratacion_ml,
            }
        )
    return resultado