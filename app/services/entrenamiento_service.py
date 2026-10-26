from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.entrenamiento import (
    EjercicioEntrenamiento,
    Entrenamiento,
    EstadoEntrenamiento,
    Serie,
)
from app.models.usuario import Usuario
from app.schemas.entrenamiento import (
    EjercicioEntrenamientoIn,
    EntrenamientoStart,
    EntrenamientoSync,
    FinalizarIn,
    SerieIn,
)
from app.services import ejercicio_service, rutina_service
from app.services.fechas import ahora_utc, hoy


class EntrenamientoNoEncontrado(Exception):
    pass


class EntrenamientoEnCurso(Exception):
    pass


class EntrenamientoNoEditable(Exception):
    pass


class DatosEntrenamientoInvalidos(Exception):
    pass


def _consulta():
    return select(Entrenamiento).options(
        selectinload(Entrenamiento.ejercicios).options(
            selectinload(EjercicioEntrenamiento.series),
            joinedload(EjercicioEntrenamiento.ejercicio),
        )
    )


def obtener_entrenamiento(db: Session, usuario: Usuario, entrenamiento_id: int) -> Entrenamiento:
    entrenamiento = db.scalar(
        _consulta()
        .where(Entrenamiento.id == entrenamiento_id)
        .execution_options(populate_existing=True)
    )
    # El entrenamiento de otra persona se trata como inexistente (RNF-15)
    if entrenamiento is None or entrenamiento.usuario_id != usuario.id:
        raise EntrenamientoNoEncontrado()
    return entrenamiento


def obtener_en_curso(db: Session, usuario: Usuario) -> Entrenamiento | None:
    return db.scalar(
        _consulta()
        .where(
            Entrenamiento.usuario_id == usuario.id,
            Entrenamiento.estado == EstadoEntrenamiento.EN_CURSO,
        )
        .execution_options(populate_existing=True)
    )


def _exigir_en_curso(entrenamiento: Entrenamiento) -> None:
    if entrenamiento.estado != EstadoEntrenamiento.EN_CURSO:
        raise EntrenamientoNoEditable()


# ---------- Iniciar ----------
def iniciar_entrenamiento(
    db: Session, usuario: Usuario, datos: EntrenamientoStart
) -> Entrenamiento:
    if obtener_en_curso(db, usuario) is not None:
        raise EntrenamientoEnCurso()

    entrenamiento = Entrenamiento(
        usuario_id=usuario.id,
        titulo="Estilo libre",
        estado=EstadoEntrenamiento.EN_CURSO,
        fecha=hoy(),
        iniciado_en=ahora_utc(),
    )

    if datos.rutina_id is not None:
        # Lanza RutinaNoEncontrada si no existe o es de otra persona
        rutina = rutina_service.obtener_rutina(db, usuario, datos.rutina_id)
        dia = next((d for d in rutina.dias if d.id == datos.dia_id), None)
        if dia is None:
            raise DatosEntrenamientoInvalidos("El día elegido no pertenece a la rutina")

        entrenamiento.rutina_id = rutina.id
        entrenamiento.titulo = f"{rutina.nombre} · {dia.nombre}"
        for posicion, item in enumerate(dia.ejercicios):
            # Series por defecto: los valores de la rutina, editables al entrenar
            series = [
                Serie(
                    numero=numero,
                    peso_kg=item.peso_sugerido_kg,
                    repeticiones=item.repeticiones,
                    completada=False,
                )
                for numero in range(1, item.series + 1)
            ]
            entrenamiento.ejercicios.append(
                EjercicioEntrenamiento(
                    ejercicio_id=item.ejercicio_id, orden=posicion, series=series
                )
            )

    db.add(entrenamiento)
    try:
        db.commit()
    except IntegrityError:
        # Dos pedidos simultáneos: gana uno solo (índice único parcial)
        db.rollback()
        raise EntrenamientoEnCurso()
    return obtener_entrenamiento(db, usuario, entrenamiento.id)


# ---------- Registrar ejercicios y series ----------
def _sincronizar_series(ejercicio: EjercicioEntrenamiento, series_in: list[SerieIn]) -> None:
    actuales = {serie.id: serie for serie in ejercicio.series}
    conservadas = {s.id for s in series_in if s.id is not None}
    if not conservadas.issubset(actuales):
        raise DatosEntrenamientoInvalidos("Una de las series no pertenece a este ejercicio")

    for serie in list(ejercicio.series):
        if serie.id not in conservadas:
            ejercicio.series.remove(serie)

    for numero, serie_in in enumerate(series_in, start=1):
        if serie_in.id is None:
            serie = Serie()
            ejercicio.series.append(serie)
        else:
            serie = actuales[serie_in.id]
        serie.numero = numero
        serie.peso_kg = serie_in.peso_kg
        serie.repeticiones = serie_in.repeticiones
        serie.completada = serie_in.completada


def _sincronizar_ejercicios(
    entrenamiento: Entrenamiento, ejercicios_in: list[EjercicioEntrenamientoIn]
) -> None:
    actuales = {e.id: e for e in entrenamiento.ejercicios}
    conservados = {e.id for e in ejercicios_in if e.id is not None}
    if not conservados.issubset(actuales):
        raise DatosEntrenamientoInvalidos("Uno de los ejercicios no pertenece a este entrenamiento")

    for ejercicio in list(entrenamiento.ejercicios):
        if ejercicio.id not in conservados:
            entrenamiento.ejercicios.remove(ejercicio)

    for posicion, ejercicio_in in enumerate(ejercicios_in):
        if ejercicio_in.id is None:
            ejercicio = EjercicioEntrenamiento()
            entrenamiento.ejercicios.append(ejercicio)
        else:
            ejercicio = actuales[ejercicio_in.id]
        ejercicio.ejercicio_id = ejercicio_in.ejercicio_id
        ejercicio.orden = posicion
        ejercicio.notas = ejercicio_in.notas
        _sincronizar_series(ejercicio, ejercicio_in.series)


def actualizar_entrenamiento(
    db: Session, usuario: Usuario, entrenamiento_id: int, datos: EntrenamientoSync
) -> Entrenamiento:
    entrenamiento = obtener_entrenamiento(db, usuario, entrenamiento_id)
    _exigir_en_curso(entrenamiento)

    try:
        pedidos = {e.ejercicio_id for e in datos.ejercicios}
        ya_usados = {e.ejercicio_id for e in entrenamiento.ejercicios}
        nuevos = pedidos - ya_usados
        if nuevos - ejercicio_service.ids_ejercicios_visibles(db, usuario, nuevos):
            raise DatosEntrenamientoInvalidos("Alguno de los ejercicios elegidos no existe")
        _sincronizar_ejercicios(entrenamiento, datos.ejercicios)
    except DatosEntrenamientoInvalidos:
        db.rollback()  # RNF-14: no dejar cambios a medias
        raise

    db.commit()
    return obtener_entrenamiento(db, usuario, entrenamiento_id)


# ---------- Finalizar y descartar ----------
def finalizar_entrenamiento(
    db: Session, usuario: Usuario, entrenamiento_id: int, datos: FinalizarIn
) -> Entrenamiento:
    entrenamiento = obtener_entrenamiento(db, usuario, entrenamiento_id)
    _exigir_en_curso(entrenamiento)

    hay_completadas = any(
        serie.completada for e in entrenamiento.ejercicios for serie in e.series
    )
    if not hay_completadas:
        raise DatosEntrenamientoInvalidos("Marcá al menos una serie como hecha para terminar")

    # Se conserva solo lo que se realizó
    for ejercicio in list(entrenamiento.ejercicios):
        for serie in list(ejercicio.series):
            if not serie.completada:
                ejercicio.series.remove(serie)
        if not ejercicio.series:
            entrenamiento.ejercicios.remove(ejercicio)

    for posicion, ejercicio in enumerate(entrenamiento.ejercicios):
        ejercicio.orden = posicion
        for numero, serie in enumerate(ejercicio.series, start=1):
            serie.numero = numero

    fin = ahora_utc()
    entrenamiento.finalizado_en = fin
    entrenamiento.duracion_segundos = max(0, int((fin - entrenamiento.iniciado_en).total_seconds()))
    entrenamiento.estado = EstadoEntrenamiento.FINALIZADO
    entrenamiento.agua_ml = datos.agua_ml
    entrenamiento.dificultad = datos.dificultad
    entrenamiento.cansancio = datos.cansancio
    entrenamiento.animo = datos.animo

    db.commit()
    return obtener_entrenamiento(db, usuario, entrenamiento_id)


def descartar_entrenamiento(db: Session, usuario: Usuario, entrenamiento_id: int) -> None:
    entrenamiento = obtener_entrenamiento(db, usuario, entrenamiento_id)
    _exigir_en_curso(entrenamiento)
    db.delete(entrenamiento)
    db.commit()