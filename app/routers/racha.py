from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.usuario import RolUsuario, Usuario
from app.schemas.habitos import RachaOut
from app.services import racha_service

router = APIRouter(prefix="/racha", tags=["Racha"])

solo_usuario = require_role(RolUsuario.USUARIO)


@router.get("", response_model=RachaOut)
def obtener(usuario: Usuario = Depends(solo_usuario), db: Session = Depends(get_db)):
    try:
        return racha_service.obtener_racha(db, usuario.id)
    except racha_service.PerfilIncompleto:
        raise HTTPException(status_code=409, detail="Completá tu perfil para ver tu racha")