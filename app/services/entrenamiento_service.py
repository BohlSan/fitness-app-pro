from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.ejercicio import Ejercicio, TipoMedicion
from app.models.entrenamiento import (
    EjercicioEntrenamiento,
    Entrenamiento,
    EstadoEntrenamiento,
    Serie,
)
from app.models.perfil import PerfilUsuario
from app.models.usuario import Usuario
from app.schemas.entrenamiento import (
    EjercicioEntrenamientoIn,
    EntrenamientoStart,
    EntrenamientoSync,
    FinalizarIn,
    SerieIn,
)
from app.services import ejercicio_service, rutina_service
from app.services.eventos import historial_entrenamientos
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


def obtener_finalizado_de(db: Session, usuario_id: int, entrenamiento_id: int) -> Entrenamiento:
    """Entrenamiento finalizado de una persona (lo usa el trainer sobre sus clientes)."""
    entrenamiento = db.scalar(
        _consulta()
        .where(Entrenamiento.id == entrenamiento_id)
        .execution_options(populate_existing=True)
    )
    if (
        entrenamiento is None
        or entrenamiento.usuario_id != usuario_id
        or entrenamiento.estado != EstadoEntrenamiento.FINALIZADO
    ):
        raise EntrenamientoNoEncontrado()
    return entrenamiento


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
        perfil = db.get(PerfilUsuario, usuario.id)
        peso_corporal = perfil.peso_actual_kg if perfil is not None else None
        for posicion, item in enumerate(dia.ejercicios):
            if item.ejercicio.tipo_medicion == TipoMedicion.TIEMPO:
                # Ejercicio por tiempo: un único registro de duración, sin repeticiones.
                series = [
                    Serie(
                        numero=1,
                        peso_kg=None,
                        repeticiones=None,
                        duracion_segundos=item.duracion_sugerida_segundos,
                        completada=False,
                    )
                ]
            else:
                # El peso corporal se copia como carga en el momento de iniciar.
                peso = peso_corporal if item.ejercicio.usa_peso_corporal else item.peso_sugerido_kg
                series = [
                    Serie(
                        numero=numero,
                        peso_kg=peso,
                        repeticiones=item.repeticiones,
                        duracion_segundos=None,
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
def _sincronizar_series(
    ejercicio: EjercicioEntrenamiento,
    series_in: list[SerieIn],
    ejercicio_catalogo: Ejercicio,
    peso_corporal: float | None,
    cambiar_ejercicio: bool = False,
) -> None:
    es_tiempo = ejercicio_catalogo.tipo_medicion == TipoMedicion.TIEMPO
    if es_tiempo and len(series_in) != 1:
        raise DatosEntrenamientoInvalidos("El ejercicio por tiempo debe tener un único registro de duración")
    if es_tiempo and any(s.duracion_segundos is None for s in series_in):
        raise DatosEntrenamientoInvalidos("Indicá la duración del ejercicio")
    if not es_tiempo and any(s.repeticiones is None for s in series_in):
        raise DatosEntrenamientoInvalidos("Indicá las repeticiones de cada serie")

    actuales = {serie.id: serie for serie in ejercicio.series}
    conservadas = {s.id for s in series_in if s.id is not None}
    if not conservadas.issubset(actuales):
        raise DatosEntrenamientoInvalidos("Una de las series no pertenece a este ejercicio")

    for serie in list(ejercicio.series):
        if serie.id not in conservadas:
            ejercicio.series.remove(serie)

    for numero, serie_in in enumerate(series_in, start=1):
        es_nueva = serie_in.id is None
        if es_nueva:
            serie = Serie()
            ejercicio.series.append(serie)
        else:
            serie = actuales[serie_in.id]
        serie.numero = numero
        serie.completada = serie_in.completada
        if es_tiempo:
            serie.peso_kg = None
            serie.repeticiones = None
            serie.duracion_segundos = serie_in.duracion_segundos
        else:
            serie.repeticiones = serie_in.repeticiones
            serie.duracion_segundos = None
            if ejercicio_catalogo.usa_peso_corporal:
                # El peso queda congelado en la serie; no cambia si luego se edita el perfil.
                if es_nueva or cambiar_ejercicio or serie.peso_kg is None:
                    serie.peso_kg = peso_corporal
            else:
                serie.peso_kg = serie_in.peso_kg


def _sincronizar_ejercicios(
    db: Session,
    entrenamiento: Entrenamiento,
    ejercicios_in: list[EjercicioEntrenamientoIn],
    peso_corporal: float | None,
) -> None:
    actuales = {e.id: e for e in entrenamiento.ejercicios}
    conservados = {e.id for e in ejercicios_in if e.id is not None}
    if not conservados.issubset(actuales):
        raise DatosEntrenamientoInvalidos("Uno de los ejercicios no pertenece a este entrenamiento")

    ids = {item.ejercicio_id for item in ejercicios_in}
    catalogo = {
        ejercicio.id: ejercicio
        for ejercicio in db.scalars(select(Ejercicio).where(Ejercicio.id.in_(ids)))
    } if ids else {}
    if len(catalogo) != len(ids):
        raise DatosEntrenamientoInvalidos("Alguno de los ejercicios elegidos no existe")

    for ejercicio in list(entrenamiento.ejercicios):
        if ejercicio.id not in conservados:
            entrenamiento.ejercicios.remove(ejercicio)

    for posicion, ejercicio_in in enumerate(ejercicios_in):
        if ejercicio_in.id is None:
            ejercicio = EjercicioEntrenamiento()
            entrenamiento.ejercicios.append(ejercicio)
            cambiar_ejercicio = True
        else:
            ejercicio = actuales[ejercicio_in.id]
            cambiar_ejercicio = ejercicio.ejercicio_id != ejercicio_in.ejercicio_id
        ejercicio_catalogo = catalogo[ejercicio_in.ejercicio_id]
        ejercicio.ejercicio_id = ejercicio_in.ejercicio_id
        ejercicio.orden = posicion
        ejercicio.notas = ejercicio_in.notas
        _sincronizar_series(
            ejercicio,
            ejercicio_in.series,
            ejercicio_catalogo,
            peso_corporal,
            cambiar_ejercicio=cambiar_ejercicio,
        )


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
        perfil = db.get(PerfilUsuario, usuario.id)
        peso_corporal = perfil.peso_actual_kg if perfil is not None else None
        _sincronizar_ejercicios(db, entrenamiento, datos.ejercicios, peso_corporal)
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

    # Observer: avisa a quienes siguen este historial (el trainer vinculado)
    historial_entrenamientos.finalizado(db, entrenamiento)

    db.commit()
    return obtener_entrenamiento(db, usuario, entrenamiento_id)


def descartar_entrenamiento(db: Session, usuario: Usuario, entrenamiento_id: int) -> None:
    entrenamiento = obtener_entrenamiento(db, usuario, entrenamiento_id)
    _exigir_en_curso(entrenamiento)
    db.delete(entrenamiento)
    db.commit()