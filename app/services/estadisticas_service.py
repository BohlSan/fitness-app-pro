from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ejercicio import Ejercicio
from app.models.entrenamiento import (
    EjercicioEntrenamiento,
    Entrenamiento,
    EstadoEntrenamiento,
    Serie,
)
from app.services import calculos
from app.services.fechas import hoy

# Todas las funciones reciben usuario_id (no el usuario logueado): en la Etapa 9
# el trainer las reutiliza sobre un cliente tras verificar el permiso (RF-29).


class PeriodoInvalido(Exception):
    pass


class SinRegistros(Exception):
    pass


def _filas_series(db: Session, usuario_id: int, ejercicio_id: int | None = None):
    """Todas las series completadas de entrenamientos finalizados, en orden cronológico."""
    consulta = (
        select(
            Entrenamiento.id.label("entrenamiento_id"),
            Entrenamiento.fecha,
            Entrenamiento.iniciado_en,
            EjercicioEntrenamiento.ejercicio_id,
            Ejercicio.nombre,
            Ejercicio.grupo_principal,
            Serie.peso_kg,
            Serie.repeticiones,
        )
        .select_from(Entrenamiento)
        .join(EjercicioEntrenamiento, EjercicioEntrenamiento.entrenamiento_id == Entrenamiento.id)
        .join(Serie, Serie.ejercicio_entrenamiento_id == EjercicioEntrenamiento.id)
        .join(Ejercicio, Ejercicio.id == EjercicioEntrenamiento.ejercicio_id)
        .where(
            Entrenamiento.usuario_id == usuario_id,
            Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
            Serie.completada.is_(True),
        )
        .order_by(Entrenamiento.fecha, Entrenamiento.id)
    )
    if ejercicio_id is not None:
        consulta = consulta.where(EjercicioEntrenamiento.ejercicio_id == ejercicio_id)
    return list(db.execute(consulta).all())


def _en_periodo(fila, desde: date | None, hasta: date | None) -> bool:
    return (desde is None or fila.fecha >= desde) and (hasta is None or fila.fecha <= hasta)


# ---------- Resumen (RF-25) ----------
def resumen(
    db: Session, usuario_id: int, desde: date | None = None, hasta: date | None = None
) -> dict:
    if desde is not None and hasta is not None and desde > hasta:
        raise PeriodoInvalido()

    filtros = [
        Entrenamiento.usuario_id == usuario_id,
        Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
    ]
    if desde is not None:
        filtros.append(Entrenamiento.fecha >= desde)
    if hasta is not None:
        filtros.append(Entrenamiento.fecha <= hasta)

    cantidad, duracion, agua, primera = db.execute(
        select(
            func.count(Entrenamiento.id),
            func.avg(Entrenamiento.duracion_segundos),
            func.avg(Entrenamiento.agua_ml),
            func.min(Entrenamiento.fecha),
        ).where(*filtros)
    ).one()

    if cantidad == 0:
        return {
            "cantidad_entrenamientos": 0,
            "frecuencia_semanal": 0.0,
            "duracion_promedio_segundos": None,
            "volumen_total_kg": 0.0,
            "agua_promedio_ml": None,
            "por_semana": [],
        }

    volumen = db.scalar(
        select(func.coalesce(func.sum(func.coalesce(Serie.peso_kg, 0) * Serie.repeticiones), 0))
        .select_from(Entrenamiento)
        .join(EjercicioEntrenamiento, EjercicioEntrenamiento.entrenamiento_id == Entrenamiento.id)
        .join(Serie, Serie.ejercicio_entrenamiento_id == EjercicioEntrenamiento.id)
        .where(*filtros, Serie.completada.is_(True))
    )

    fin = hasta or hoy()
    inicio = desde or primera
    dias = max((fin - inicio).days + 1, 1)
    frecuencia = round(cantidad / max(dias / 7, 1), 2)

    fechas = list(db.scalars(select(Entrenamiento.fecha).where(*filtros)))
    inicio_grafico = max(inicio, fin - timedelta(weeks=52))

    return {
        "cantidad_entrenamientos": cantidad,
        "frecuencia_semanal": frecuencia,
        "duracion_promedio_segundos": float(duracion) if duracion is not None else None,
        "volumen_total_kg": round(float(volumen), 2),
        "agua_promedio_ml": float(agua) if agua is not None else None,
        "por_semana": calculos.entrenamientos_por_semana(fechas, inicio_grafico, fin),
    }


# ---------- Ejercicios (RF-23 y RF-24) ----------
def ejercicios_entrenados(db: Session, usuario_id: int) -> list[dict]:
    """Ejercicios que la persona entrenó, con sus mejores marcas."""
    por_ejercicio = defaultdict(list)
    for fila in _filas_series(db, usuario_id):
        por_ejercicio[fila.ejercicio_id].append(fila)

    resultado = []
    for ejercicio_id, filas in por_ejercicio.items():
        marcas = calculos.mejores_marcas(filas)
        resultado.append(
            {
                "ejercicio_id": ejercicio_id,
                "nombre": filas[0].nombre,
                "grupo_principal": filas[0].grupo_principal,
                "sesiones": len({f.entrenamiento_id for f in filas}),
                "ultima_fecha": max(f.fecha for f in filas),
                "mayor_peso_kg": marcas["mayor_peso"]["peso_kg"] if marcas["mayor_peso"] else None,
                "mejor_volumen_sesion_kg": (
                    marcas["mejor_volumen_sesion"]["volumen_kg"]
                    if marcas["mejor_volumen_sesion"]
                    else None
                ),
            }
        )
    resultado.sort(key=lambda r: r["nombre"].lower())
    resultado.sort(key=lambda r: r["ultima_fecha"], reverse=True)
    return resultado


def evolucion_ejercicio(
    db: Session,
    usuario_id: int,
    ejercicio_id: int,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict:
    """Evolución por sesión y volumen del período; las marcas son de todo el historial."""
    if desde is not None and hasta is not None and desde > hasta:
        raise PeriodoInvalido()

    filas = _filas_series(db, usuario_id, ejercicio_id)
    if not filas:
        raise SinRegistros()

    sesiones = calculos.volumen_por_sesion([f for f in filas if _en_periodo(f, desde, hasta)])
    return {
        "ejercicio_id": ejercicio_id,
        "nombre": filas[0].nombre,
        "grupo_principal": filas[0].grupo_principal,
        "volumen_total_kg": round(sum(s["volumen_kg"] for s in sesiones), 2),
        "sesiones": sesiones,
        "marcas": calculos.mejores_marcas(filas),
    }


# ---------- Récords de una sesión (RF-24) ----------
def prs_de_entrenamiento(db: Session, usuario_id: int, entrenamiento_id: int) -> list[dict]:
    entrenamiento = db.get(Entrenamiento, entrenamiento_id)
    if (
        entrenamiento is None
        or entrenamiento.usuario_id != usuario_id
        or entrenamiento.estado != EstadoEntrenamiento.FINALIZADO
    ):
        raise SinRegistros()

    previas = defaultdict(list)
    sesion = defaultdict(list)
    nombres = {}
    for fila in _filas_series(db, usuario_id):
        nombres[fila.ejercicio_id] = fila.nombre
        if fila.entrenamiento_id == entrenamiento_id:
            sesion[fila.ejercicio_id].append(fila)
        elif fila.iniciado_en < entrenamiento.iniciado_en:
            previas[fila.ejercicio_id].append(fila)

    resultado = []
    for ejercicio_id, filas_sesion in sesion.items():
        for pr in calculos.detectar_prs(previas.get(ejercicio_id, []), filas_sesion):
            resultado.append(
                {"ejercicio_id": ejercicio_id, "nombre": nombres[ejercicio_id], "peso_kg": None, **pr}
            )
    return resultado