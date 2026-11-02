import secrets

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.trainer import (
    AsignacionRutina,
    EstadoAsignacion,
    EstadoCuota,
    EstadoVinculo,
    PagoCliente,
    PerfilTrainer,
    VinculoTrainer,
)
from app.models.usuario import Usuario
from app.schemas.trainer import PagoIn
from app.services import auditoria_service
from app.services.fechas import hoy

# Sin 0/O ni 1/I/L: el código se puede dictar sin confusiones
ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
LARGO_CODIGO = 8
VIVOS = (EstadoVinculo.PENDIENTE, EstadoVinculo.ACTIVA)


class CodigoInvalido(Exception):
    pass


class YaTieneEntrenador(Exception):
    pass


class VinculoNoEncontrado(Exception):
    pass


class EstadoInvalido(Exception):
    pass


class ClienteNoAutorizado(Exception):
    pass


class DatosPagoInvalidos(Exception):
    pass


# ---------- Código de enlace ----------
def _codigo_nuevo(db: Session) -> str:
    while True:
        codigo = "".join(secrets.choice(ALFABETO) for _ in range(LARGO_CODIGO))
        if db.scalar(select(PerfilTrainer.usuario_id).where(PerfilTrainer.codigo_enlace == codigo)) is None:
            return codigo


def obtener_codigo(db: Session, trainer: Usuario) -> str:
    perfil = db.get(PerfilTrainer, trainer.id)
    if perfil is None:
        perfil = PerfilTrainer(usuario_id=trainer.id, codigo_enlace=_codigo_nuevo(db))
        db.add(perfil)
        db.commit()
    return perfil.codigo_enlace


def regenerar_codigo(db: Session, trainer: Usuario) -> str:
    obtener_codigo(db, trainer)  # se asegura de que exista
    perfil = db.get(PerfilTrainer, trainer.id)
    perfil.codigo_enlace = _codigo_nuevo(db)
    db.commit()
    return perfil.codigo_enlace


# ---------- Relación ----------
def vinculo_vivo_de_cliente(db: Session, cliente_id: int) -> VinculoTrainer | None:
    return db.scalar(
        select(VinculoTrainer).where(
            VinculoTrainer.cliente_id == cliente_id, VinculoTrainer.estado.in_(VIVOS)
        )
    )


def solicitar_vinculo(db: Session, cliente: Usuario, codigo: str) -> VinculoTrainer:
    perfil_trainer = db.scalar(
        select(PerfilTrainer).where(PerfilTrainer.codigo_enlace == codigo.strip().upper())
    )
    if perfil_trainer is None:
        raise CodigoInvalido()
    if vinculo_vivo_de_cliente(db, cliente.id) is not None:
        raise YaTieneEntrenador()

    vinculo = VinculoTrainer(
        trainer_id=perfil_trainer.usuario_id,
        cliente_id=cliente.id,
        estado=EstadoVinculo.PENDIENTE,
        estado_cuota=EstadoCuota.PENDIENTE,
    )
    db.add(vinculo)
    try:
        db.flush()
    except IntegrityError:
        # Dos pedidos simultáneos: el índice único deja pasar uno solo
        db.rollback()
        raise YaTieneEntrenador()
    auditoria_service.registrar(db, cliente, "SOLICITAR_VINCULO", "vinculo", vinculo.id)
    db.commit()
    return vinculo


def _vinculo_del_trainer(db: Session, trainer_id: int, vinculo_id: int) -> VinculoTrainer:
    vinculo = db.get(VinculoTrainer, vinculo_id)
    if vinculo is None or vinculo.trainer_id != trainer_id:
        raise VinculoNoEncontrado()
    return vinculo


def aceptar(db: Session, trainer: Usuario, vinculo_id: int) -> VinculoTrainer:
    vinculo = _vinculo_del_trainer(db, trainer.id, vinculo_id)
    if vinculo.estado != EstadoVinculo.PENDIENTE:
        raise EstadoInvalido()
    vinculo.estado = EstadoVinculo.ACTIVA
    vinculo.inicio = hoy()
    auditoria_service.registrar(db, trainer, "ACEPTAR_VINCULO", "vinculo", vinculo.id)
    db.commit()
    return vinculo


def _cerrar(db: Session, vinculo: VinculoTrainer, actor: Usuario) -> VinculoTrainer:
    vinculo.estado = EstadoVinculo.FINALIZADA
    vinculo.fin = hoy()
    # Al terminar la relación, las rutinas asignadas dejan de estar activas
    db.execute(
        update(AsignacionRutina)
        .where(
            AsignacionRutina.trainer_id == vinculo.trainer_id,
            AsignacionRutina.cliente_id == vinculo.cliente_id,
            AsignacionRutina.estado == EstadoAsignacion.ACTIVA,
        )
        .values(estado=EstadoAsignacion.FINALIZADA)
    )
    auditoria_service.registrar(db, actor, "FINALIZAR_VINCULO", "vinculo", vinculo.id)
    db.commit()
    return vinculo


def finalizar_como_trainer(db: Session, trainer: Usuario, vinculo_id: int) -> VinculoTrainer:
    vinculo = _vinculo_del_trainer(db, trainer.id, vinculo_id)
    if vinculo.estado not in VIVOS:
        raise EstadoInvalido()
    return _cerrar(db, vinculo, trainer)


def finalizar_como_cliente(db: Session, cliente: Usuario) -> VinculoTrainer:
    vinculo = vinculo_vivo_de_cliente(db, cliente.id)
    if vinculo is None:
        raise VinculoNoEncontrado()
    return _cerrar(db, vinculo, cliente)


# ---------- Control de acceso (RF-13 y RF-30) ----------
def es_cliente_activo(db: Session, trainer_id: int, cliente_id: int) -> bool:
    return (
        db.scalar(
            select(VinculoTrainer.id).where(
                VinculoTrainer.trainer_id == trainer_id,
                VinculoTrainer.cliente_id == cliente_id,
                VinculoTrainer.estado == EstadoVinculo.ACTIVA,
            )
        )
        is not None
    )


def exigir_cliente_activo(db: Session, trainer_id: int, cliente_id: int) -> VinculoTrainer:
    """Única puerta de acceso a los datos de un cliente: relación ACTIVA o nada."""
    vinculo = db.scalar(
        select(VinculoTrainer).where(
            VinculoTrainer.trainer_id == trainer_id,
            VinculoTrainer.cliente_id == cliente_id,
            VinculoTrainer.estado == EstadoVinculo.ACTIVA,
        )
    )
    if vinculo is None:
        raise ClienteNoAutorizado()
    return vinculo


# ---------- Cuota y pagos ----------
def cambiar_cuota(
    db: Session, trainer: Usuario, cliente_id: int, estado_cuota: EstadoCuota
) -> VinculoTrainer:
    vinculo = exigir_cliente_activo(db, trainer.id, cliente_id)
    vinculo.estado_cuota = estado_cuota
    auditoria_service.registrar(db, trainer, "CAMBIAR_CUOTA", "vinculo", vinculo.id)
    db.commit()
    return vinculo


def registrar_pago(db: Session, trainer: Usuario, cliente_id: int, datos: PagoIn) -> PagoCliente:
    vinculo = exigir_cliente_activo(db, trainer.id, cliente_id)
    fecha = datos.fecha or hoy()
    if fecha > hoy():
        raise DatosPagoInvalidos("La fecha del pago no puede ser futura")

    pago = PagoCliente(vinculo_id=vinculo.id, fecha=fecha, monto=datos.monto, concepto=datos.concepto)
    db.add(pago)
    vinculo.estado_cuota = EstadoCuota.AL_DIA  # registrar un pago deja la cuota al día
    db.flush()
    auditoria_service.registrar(db, trainer, "REGISTRAR_PAGO", "pago", pago.id)
    db.commit()
    return pago


def listar_pagos(db: Session, vinculo_id: int) -> list[PagoCliente]:
    return list(
        db.scalars(
            select(PagoCliente)
            .where(PagoCliente.vinculo_id == vinculo_id)
            .order_by(PagoCliente.fecha.desc(), PagoCliente.id.desc())
        )
    )