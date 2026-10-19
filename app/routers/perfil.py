from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.usuario import RolUsuario, Usuario
from app.schemas.perfil import PerfilCreate, PerfilOut, PerfilUpdate
from app.services import perfil_service

router = APIRouter(prefix="/perfil", tags=["Perfil"])

solo_usuario = require_role(RolUsuario.USUARIO)


@router.get("", response_model=PerfilOut)
def obtener(usuario: Usuario = Depends(solo_usuario), db: Session = Depends(get_db)):
    perfil = perfil_service.obtener_perfil(db, usuario.id)
    if perfil is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todavía no completaste tu perfil",
        )
    return perfil


@router.post("", response_model=PerfilOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: PerfilCreate,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        return perfil_service.crear_perfil(db, usuario, datos)
    except perfil_service.PerfilYaExiste:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya completaste tu perfil"
        )
    except perfil_service.DatosPerfilInvalidos as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )


@router.patch("", response_model=PerfilOut)
def actualizar(
    cambios: PerfilUpdate,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        return perfil_service.actualizar_perfil(db, usuario, cambios)
    except perfil_service.PerfilNoEncontrado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todavía no completaste tu perfil",
        )
    except perfil_service.DatosPerfilInvalidos as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        )