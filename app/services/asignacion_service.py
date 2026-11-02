from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.trainer import AsignacionRutina, EstadoAsignacion
from app.models.usuario import Usuario
from app.services import auditoria_service, rutina_service, vinculo_service
from app.services.fechas import hoy


class RutinaNoAsignable(Exception):
    pass


class AsignacionNoEncontrada(Exception):
    pass


def asignar_rutina(
    db: Session, trainer: Usuario, cliente_id: int, rutina_id: int
) -> AsignacionRutina:
    vinculo_service.exigir_cliente_activo(db, trainer.id, cliente_id)

    # Lanza RutinaNoEncontrada si no existe o no es accesible para el trainer
    origen = rutina_service.obtener_rutina(db, trainer, rutina_id)
    if origen.propietario_id != trainer.id:
        raise RutinaNoAsignable()  # solo se asignan rutinas propias

    # Cada cliente recibe su propia copia: personalizarla no afecta a la plantilla
    copia = rutina_service.copiar_rutina(origen, propietario_id=cliente_id, autor_id=trainer.id)
    db.add(copia)
    db.flush()

    asignacion = AsignacionRutina(
        trainer_id=trainer.id,
        cliente_id=cliente_id,
        rutina_id=copia.id,
        rutina_nombre=copia.nombre,
        fecha_asignacion=hoy(),
        estado=EstadoAsignacion.ACTIVA,
    )
    db.add(asignacion)
    db.flush()
    auditoria_service.registrar(db, trainer, "ASIGNAR_RUTINA", "asignacion", asignacion.id)
    db.commit()
    return asignacion


def listar_asignaciones(db: Session, trainer_id: int, cliente_id: int) -> list[AsignacionRutina]:
    return list(
        db.scalars(
            select(AsignacionRutina)
            .where(
                AsignacionRutina.trainer_id == trainer_id,
                AsignacionRutina.cliente_id == cliente_id,
            )
            .order_by(AsignacionRutina.fecha_asignacion.desc(), AsignacionRutina.id.desc())
        )
    )


def finalizar_asignacion(
    db: Session, trainer: Usuario, cliente_id: int, asignacion_id: int
) -> AsignacionRutina:
    vinculo_service.exigir_cliente_activo(db, trainer.id, cliente_id)
    asignacion = db.get(AsignacionRutina, asignacion_id)
    if (
        asignacion is None
        or asignacion.trainer_id != trainer.id
        or asignacion.cliente_id != cliente_id
    ):
        raise AsignacionNoEncontrada()
    asignacion.estado = EstadoAsignacion.FINALIZADA
    db.commit()
    return asignacion