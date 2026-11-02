from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.entrenamiento import Entrenamiento, EstadoEntrenamiento
from app.models.perfil import PerfilUsuario
from app.models.trainer import ActividadCliente, EstadoVinculo, VinculoTrainer
from app.models.usuario import Usuario
from app.services import vinculo_service
from app.services.fechas import calcular_edad, hoy


def _consulta_clientes(trainer_id: int):
    return (
        select(VinculoTrainer, Usuario, PerfilUsuario.objetivo)
        .join(Usuario, Usuario.id == VinculoTrainer.cliente_id)
        .outerjoin(PerfilUsuario, PerfilUsuario.usuario_id == VinculoTrainer.cliente_id)
        .where(VinculoTrainer.trainer_id == trainer_id)
    )


def _ultimos_entrenamientos(db: Session, cliente_ids: list[int]) -> dict:
    if not cliente_ids:
        return {}
    filas = db.execute(
        select(Entrenamiento.usuario_id, func.max(Entrenamiento.fecha))
        .where(
            Entrenamiento.usuario_id.in_(cliente_ids),
            Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
        )
        .group_by(Entrenamiento.usuario_id)
    ).all()
    return dict(filas)


def _resumen(vinculo, usuario, objetivo, ultimos: dict) -> dict:
    ultimo = ultimos.get(vinculo.cliente_id)
    return {
        "vinculo_id": vinculo.id,
        "estado": vinculo.estado,
        "estado_cuota": vinculo.estado_cuota,
        "inicio": vinculo.inicio,
        "solicitado_en": vinculo.solicitado_en,
        "cliente": {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email},
        "objetivo": objetivo,
        "ultimo_entrenamiento": ultimo,
        "dias_sin_entrenar": (hoy() - ultimo).days if ultimo else None,
    }


def listar_clientes(
    db: Session, trainer_id: int, estado: EstadoVinculo | None = None
) -> list[dict]:
    consulta = _consulta_clientes(trainer_id)
    if estado is None:
        consulta = consulta.where(VinculoTrainer.estado.in_(vinculo_service.VIVOS))
    else:
        consulta = consulta.where(VinculoTrainer.estado == estado)
    filas = db.execute(consulta.order_by(func.lower(Usuario.nombre))).all()

    ultimos = _ultimos_entrenamientos(db, [vinculo.cliente_id for vinculo, _, _ in filas])
    return [_resumen(vinculo, usuario, objetivo, ultimos) for vinculo, usuario, objetivo in filas]


def resumen_vinculo(db: Session, trainer_id: int, vinculo_id: int) -> dict:
    vinculo, usuario, objetivo = db.execute(
        _consulta_clientes(trainer_id).where(VinculoTrainer.id == vinculo_id)
    ).one()
    ultimos = _ultimos_entrenamientos(db, [vinculo.cliente_id])
    return _resumen(vinculo, usuario, objetivo, ultimos)


def panel(db: Session, trainer: Usuario) -> dict:
    def contar(estado: EstadoVinculo) -> int:
        return db.scalar(
            select(func.count(VinculoTrainer.id)).where(
                VinculoTrainer.trainer_id == trainer.id, VinculoTrainer.estado == estado
            )
        )

    sin_leer = db.scalar(
        select(func.count(ActividadCliente.id)).where(
            ActividadCliente.trainer_id == trainer.id, ActividadCliente.leida.is_(False)
        )
    )
    return {
        "nombre": trainer.nombre,
        "codigo_enlace": vinculo_service.obtener_codigo(db, trainer),
        "clientes_activos": contar(EstadoVinculo.ACTIVA),
        "solicitudes_pendientes": contar(EstadoVinculo.PENDIENTE),
        "actividad_sin_leer": sin_leer,
    }


def detalle_cliente(db: Session, trainer_id: int, cliente_id: int) -> dict:
    """Información básica del cliente: solo lo necesario para acompañarlo."""
    vinculo = vinculo_service.exigir_cliente_activo(db, trainer_id, cliente_id)
    usuario = db.get(Usuario, cliente_id)
    perfil = db.get(PerfilUsuario, cliente_id)
    return {
        "vinculo_id": vinculo.id,
        "estado": vinculo.estado,
        "estado_cuota": vinculo.estado_cuota,
        "inicio": vinculo.inicio,
        "id": usuario.id,
        "nombre": usuario.nombre,
        "email": usuario.email,
        "edad": calcular_edad(perfil.fecha_nacimiento) if perfil else None,
        "altura_cm": perfil.altura_cm if perfil else None,
        "peso_actual_kg": perfil.peso_actual_kg if perfil else None,
        "objetivo": perfil.objetivo if perfil else None,
        "dias_entrenamiento_semana": perfil.dias_entrenamiento_semana if perfil else None,
    }


def mi_vinculo(db: Session, cliente_id: int) -> dict | None:
    """La relación vigente vista desde el cliente."""
    vinculo = vinculo_service.vinculo_vivo_de_cliente(db, cliente_id)
    if vinculo is None:
        return None
    trainer = db.get(Usuario, vinculo.trainer_id)
    return {
        "vinculo_id": vinculo.id,
        "estado": vinculo.estado,
        "estado_cuota": vinculo.estado_cuota,
        "inicio": vinculo.inicio,
        "trainer": {"id": trainer.id, "nombre": trainer.nombre},
        "pagos": vinculo_service.listar_pagos(db, vinculo.id),
    }


# ---------- Novedades generadas por el Observer ----------
def actividad(
    db: Session, trainer_id: int, solo_no_leidas: bool = False, limite: int = 30
) -> list[dict]:
    consulta = (
        select(ActividadCliente, Usuario)
        .join(Usuario, Usuario.id == ActividadCliente.cliente_id)
        .where(ActividadCliente.trainer_id == trainer_id)
    )
    if solo_no_leidas:
        consulta = consulta.where(ActividadCliente.leida.is_(False))
    filas = db.execute(
        consulta.order_by(ActividadCliente.creada_en.desc(), ActividadCliente.id.desc()).limit(limite)
    ).all()
    return [
        {
            "id": registro.id,
            "cliente": {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email},
            "tipo": registro.tipo,
            "entrenamiento_id": registro.entrenamiento_id,
            "titulo": registro.titulo,
            "fecha": registro.fecha,
            "duracion_segundos": registro.duracion_segundos,
            "volumen_kg": registro.volumen_kg,
            "creada_en": registro.creada_en,
            "leida": registro.leida,
        }
        for registro, usuario in filas
    ]


def marcar_actividad_leida(db: Session, trainer_id: int) -> None:
    db.execute(
        update(ActividadCliente)
        .where(ActividadCliente.trainer_id == trainer_id, ActividadCliente.leida.is_(False))
        .values(leida=True)
    )
    db.commit()