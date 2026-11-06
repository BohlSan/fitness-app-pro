from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.ejercicio import Ejercicio, TipoMedicion
from app.models.rutina import DiaRutina, Rutina, RutinaEjercicio
from app.models.trainer import AsignacionRutina, EstadoAsignacion
from app.models.usuario import RolUsuario, Usuario
from app.schemas.rutina import EjercicioRutinaIn, RutinaIn
from app.services import auditoria_service, ejercicio_service, vinculo_service


class RutinaNoEncontrada(Exception):
    pass


class DatosRutinaInvalidos(Exception):
    pass


def _consulta():
    """Rutina con sus días, ejercicios y datos del ejercicio, en pocas consultas."""
    return select(Rutina).options(
        selectinload(Rutina.dias)
        .selectinload(DiaRutina.ejercicios)
        .joinedload(RutinaEjercicio.ejercicio)
    )


def _puede_acceder(db: Session, usuario: Usuario, rutina: Rutina) -> bool:
    if rutina.propietario_id == usuario.id:
        return True
    # RF-09 y RF-30: el trainer que armó la rutina de un cliente la gestiona
    # mientras la relación con ese cliente siga activa
    return (
        usuario.rol == RolUsuario.PERSONAL_TRAINER
        and rutina.autor_id == usuario.id
        and vinculo_service.es_cliente_activo(db, usuario.id, rutina.propietario_id)
    )


def copiar_rutina(origen: Rutina, propietario_id: int, autor_id: int) -> Rutina:
    """Copia una rutina para otra persona (la asignación de un trainer a su cliente)."""
    copia = Rutina(
        nombre=origen.nombre,
        descripcion=origen.descripcion,
        autor_id=autor_id,
        propietario_id=propietario_id,
    )
    for dia in origen.dias:
        nuevo_dia = DiaRutina(dia_semana=dia.dia_semana, nombre=dia.nombre)
        for item in dia.ejercicios:
            nuevo_dia.ejercicios.append(
                RutinaEjercicio(
                    ejercicio_id=item.ejercicio_id,
                    orden=item.orden,
                    series=item.series,
                    repeticiones=item.repeticiones,
                    duracion_sugerida_segundos=item.duracion_sugerida_segundos,
                    peso_sugerido_kg=item.peso_sugerido_kg,
                    descanso_segundos=item.descanso_segundos,
                )
            )
        copia.dias.append(nuevo_dia)
    return copia


def listar_rutinas(db: Session, usuario: Usuario) -> list[Rutina]:
    consulta = _consulta().where(Rutina.propietario_id == usuario.id).order_by(Rutina.id.desc())
    return list(db.scalars(consulta))


def obtener_rutina(db: Session, usuario: Usuario, rutina_id: int) -> Rutina:
    rutina = db.scalar(
        _consulta().where(Rutina.id == rutina_id).execution_options(populate_existing=True)
    )
    # La rutina de otra persona se trata como inexistente (RNF-15)
    if rutina is None or not _puede_acceder(db, usuario, rutina):
        raise RutinaNoEncontrada()
    return rutina


def _validar_ejercicios(db: Session, usuario: Usuario, rutina: Rutina, datos: RutinaIn) -> None:
    pedidos = {e.ejercicio_id for dia in datos.dias for e in dia.ejercicios}
    ya_usados = {item.ejercicio_id for dia in rutina.dias for item in dia.ejercicios}
    # Los que ya estaban en la rutina se conservan; solo se validan los nuevos
    nuevos = pedidos - ya_usados
    if nuevos - ejercicio_service.ids_ejercicios_visibles(db, usuario, nuevos):
        raise DatosRutinaInvalidos("Alguno de los ejercicios elegidos no existe")

    ejercicios = {
        ejercicio.id: ejercicio
        for ejercicio in db.scalars(select(Ejercicio).where(Ejercicio.id.in_(pedidos)))
    } if pedidos else {}
    for dia in datos.dias:
        for item in dia.ejercicios:
            ejercicio = ejercicios.get(item.ejercicio_id)
            if ejercicio is None:
                raise DatosRutinaInvalidos("Alguno de los ejercicios elegidos no existe")
            es_tiempo = ejercicio.tipo_medicion == TipoMedicion.TIEMPO
            tiene_duracion = item.duracion_sugerida_segundos is not None
            if es_tiempo != tiene_duracion:
                raise DatosRutinaInvalidos(
                    "Los ejercicios medidos por tiempo requieren duración; los de fuerza requieren series y repeticiones"
                )
            if ejercicio.usa_peso_corporal and item.peso_sugerido_kg is not None:
                raise DatosRutinaInvalidos(
                    "El peso de los ejercicios con peso corporal se toma automáticamente del perfil"
                )


def _sincronizar_ejercicios(dia: DiaRutina, ejercicios_in: list[EjercicioRutinaIn]) -> None:
    actuales = {item.id: item for item in dia.ejercicios}
    conservados = {e.id for e in ejercicios_in if e.id is not None}
    if not conservados.issubset(actuales):
        raise DatosRutinaInvalidos("Uno de los ejercicios no pertenece a esta rutina")

    for item in list(dia.ejercicios):
        if item.id not in conservados:
            dia.ejercicios.remove(item)  # delete-orphan lo borra

    for posicion, ejercicio_in in enumerate(ejercicios_in):
        if ejercicio_in.id is None:
            item = RutinaEjercicio()
            dia.ejercicios.append(item)
        else:
            item = actuales[ejercicio_in.id]
        item.ejercicio_id = ejercicio_in.ejercicio_id
        item.orden = posicion
        item.series = ejercicio_in.series
        item.repeticiones = ejercicio_in.repeticiones
        item.duracion_sugerida_segundos = ejercicio_in.duracion_sugerida_segundos
        item.peso_sugerido_kg = ejercicio_in.peso_sugerido_kg
        item.descanso_segundos = ejercicio_in.descanso_segundos


def _sincronizar_dias(rutina: Rutina, dias_in) -> None:
    actuales = {dia.id: dia for dia in rutina.dias}
    conservados = {d.id for d in dias_in if d.id is not None}
    if not conservados.issubset(actuales):
        raise DatosRutinaInvalidos("Uno de los días no pertenece a esta rutina")

    for dia in list(rutina.dias):
        if dia.id not in conservados:
            rutina.dias.remove(dia)

    for dia_in in dias_in:
        if dia_in.id is None:
            dia = DiaRutina()
            rutina.dias.append(dia)
        else:
            dia = actuales[dia_in.id]
        dia.dia_semana = dia_in.dia_semana
        dia.nombre = dia_in.nombre
        _sincronizar_ejercicios(dia, dia_in.ejercicios)


def _sincronizar(db: Session, usuario: Usuario, rutina: Rutina, datos: RutinaIn) -> None:
    try:
        _validar_ejercicios(db, usuario, rutina, datos)
        _sincronizar_dias(rutina, datos.dias)
    except DatosRutinaInvalidos:
        db.rollback()  # RNF-14: no dejar cambios a medias
        raise


def crear_rutina(db: Session, usuario: Usuario, datos: RutinaIn) -> Rutina:
    rutina = Rutina(
        nombre=datos.nombre,
        descripcion=datos.descripcion,
        autor_id=usuario.id,
        propietario_id=usuario.id,
    )
    _sincronizar(db, usuario, rutina, datos)
    db.add(rutina)
    db.flush()
    rutina_id = rutina.id
    auditoria_service.registrar(db, usuario, "CREAR_RUTINA", "rutina", rutina_id)
    db.commit()
    return obtener_rutina(db, usuario, rutina_id)


def actualizar_rutina(
    db: Session, usuario: Usuario, rutina_id: int, datos: RutinaIn
) -> Rutina:
    rutina = obtener_rutina(db, usuario, rutina_id)
    rutina.nombre = datos.nombre
    rutina.descripcion = datos.descripcion
    _sincronizar(db, usuario, rutina, datos)
    auditoria_service.registrar(db, usuario, "MODIFICAR_RUTINA", "rutina", rutina_id)
    db.commit()
    return obtener_rutina(db, usuario, rutina_id)


def eliminar_rutina(db: Session, usuario: Usuario, rutina_id: int) -> None:
    rutina = obtener_rutina(db, usuario, rutina_id)
    auditoria_service.registrar(db, usuario, "ELIMINAR_RUTINA", "rutina", rutina_id)
    db.execute(
        update(AsignacionRutina)
        .where(AsignacionRutina.rutina_id == rutina_id)
        .values(estado=EstadoAsignacion.FINALIZADA)
    )
    db.delete(rutina)
    db.commit()