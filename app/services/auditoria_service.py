from sqlalchemy.orm import Session

from app.models.auditoria import RegistroAuditoria
from app.models.usuario import Usuario


def registrar(
    db: Session,
    usuario: Usuario,
    accion: str,
    entidad: str,
    entidad_id: int | None = None,
) -> None:
    """Agrega el registro a la sesión sin confirmarlo.

    Se guarda junto con la operación que lo originó: si esa falla, no queda
    un registro de algo que no pasó (RNF-14 y RNF-16).
    """
    db.add(
        RegistroAuditoria(
            usuario_id=usuario.id,
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
        )
    )