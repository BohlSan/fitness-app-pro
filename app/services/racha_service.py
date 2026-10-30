from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entrenamiento import Entrenamiento, EstadoEntrenamiento
from app.models.perfil import PerfilUsuario
from app.services import calculos
from app.services.fechas import hoy
from app.services.peso_service import PerfilIncompleto  # noqa: F401  (se reutiliza)


def obtener_racha(db: Session, usuario_id: int) -> dict:
    perfil = db.get(PerfilUsuario, usuario_id)
    if perfil is None:
        raise PerfilIncompleto()

    fechas = list(
        db.scalars(
            select(Entrenamiento.fecha).where(
                Entrenamiento.usuario_id == usuario_id,
                Entrenamiento.estado == EstadoEntrenamiento.FINALIZADO,
            )
        )
    )
    return calculos.calcular_racha(fechas, perfil.dias_entrenamiento_semana, hoy())