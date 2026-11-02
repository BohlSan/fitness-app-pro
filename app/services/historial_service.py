import calendar
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.entrenamiento import (
    EjercicioEntrenamiento,
    Entrenamiento,
    EstadoEntrenamiento,
)


class PeriodoInvalido(Exception):
    pass


def _consulta():
    return select(Entrenamiento).options(
        selectinload(Entrenamiento.ejercicios).options(
            selectinload(EjercicioEntrenamiento.series),
            joinedload(EjercicioEntrenamiento.ejercicio),
        )
    )


def listar_historial(
    db: Session,
    usuario_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = 20,
    offset: int = 0,
) -> list[Entrenamiento]:
    """Entrenamientos finalizados de la persona, del más reciente al más antiguo."""
    if desde is not None and hasta is not None and desde > hasta:
        raise PeriodoInvalido()

    consulta = _consulta().where(
        Entrenamiento.usuario_id == usuario_id,
        Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
    )
    if desde is not None:
        consulta = consulta.where(Entrenamiento.fecha >= desde)
    if hasta is not None:
        consulta = consulta.where(Entrenamiento.fecha <= hasta)

    consulta = (
        consulta.order_by(Entrenamiento.fecha.desc(), Entrenamiento.iniciado_en.desc())
        .limit(limite)
        .offset(offset)
        .execution_options(populate_existing=True)
    )
    return list(db.scalars(consulta))


def calendario_mensual(db: Session, usuario_id: int, anio: int, mes: int) -> list[dict]:
    """Por cada día del mes con entrenamientos: cuántos y la dificultad más alta."""
    primero = date(anio, mes, 1)
    ultimo = date(anio, mes, calendar.monthrange(anio, mes)[1])

    filas = db.execute(
        select(
            Entrenamiento.fecha,
            func.count(Entrenamiento.id),
            func.max(Entrenamiento.dificultad),
        )
        .where(
            Entrenamiento.usuario_id == usuario_id,
            Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
            Entrenamiento.fecha >= primero,
            Entrenamiento.fecha <= ultimo,
        )
        .group_by(Entrenamiento.fecha)
        .order_by(Entrenamiento.fecha)
    ).all()

    return [
        {"fecha": fecha, "cantidad": cantidad, "dificultad_max": dificultad}
        for fecha, cantidad, dificultad in filas
    ]