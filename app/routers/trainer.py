from fastapi import APIRouter, Depends

from app.dependencies import require_role
from app.models.usuario import RolUsuario, Usuario

router = APIRouter(prefix="/trainer", tags=["Personal Trainer"])


@router.get("/panel")
def panel_trainer(
    usuario: Usuario = Depends(require_role(RolUsuario.PERSONAL_TRAINER)),
):
    # Placeholder de la Etapa 1 para comprobar RF-04.
    # Se reemplaza por el dashboard real en la Etapa 9.
    return {"mensaje": f"Panel de trainer de {usuario.nombre}"}