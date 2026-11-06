import calendar
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.rutina import DiaRutina, DiaSemana, Rutina
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


def calendario_planificado(db: Session, usuario_id: int, anio: int, mes: int) -> list[dict]:
    """Días del mes con rutinas previstas, incluyendo todas las rutinas coincidentes."""
    primero = date(anio, mes, 1)
    ultimo = date(anio, mes, calendar.monthrange(anio, mes)[1])

    filas = db.execute(
        select(Rutina.nombre, DiaRutina.nombre, DiaRutina.dia_semana)
        .join(DiaRutina, DiaRutina.rutina_id == Rutina.id)
        .where(Rutina.propietario_id == usuario_id)
        .order_by(Rutina.nombre, DiaRutina.nombre)
    ).all()

    por_dia = {dia: [] for dia in DiaSemana}
    for rutina_nombre, dia_nombre, dia_semana in filas:
        por_dia[dia_semana].append(
            {"rutina_nombre": rutina_nombre, "dia_nombre": dia_nombre}
        )

    resultado = []
    fecha = primero
    dias_por_numero = list(DiaSemana)
    while fecha <= ultimo:
        rutinas = por_dia[dias_por_numero[fecha.weekday()]]
        if rutinas:
            resultado.append({"fecha": fecha, "rutinas": rutinas})
        fecha = date.fromordinal(fecha.toordinal() + 1)
    return resultado