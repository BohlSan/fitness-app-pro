from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.usuario import RolUsuario, Usuario
from app.schemas.trainer import MiVinculoOut, VinculoIn
from app.services import trainer_service, vinculo_service

router = APIRouter(prefix="/vinculo", tags=["Relación con el entrenador"])

solo_usuario = require_role(RolUsuario.USUARIO)


@router.get("", response_model=MiVinculoOut | None)
def mi_vinculo(usuario: Usuario = Depends(solo_usuario), db: Session = Depends(get_db)):
    return trainer_service.mi_vinculo(db, usuario.id)


@router.post("", response_model=MiVinculoOut, status_code=status.HTTP_201_CREATED)
def solicitar(
    datos: VinculoIn,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        vinculo_service.solicitar_vinculo(db, usuario, datos.codigo)
    except vinculo_service.CodigoInvalido:
        raise HTTPException(status_code=404, detail="El código no existe. Revisalo con tu entrenador")
    except vinculo_service.YaTieneEntrenador:
        raise HTTPException(
            status_code=409, detail="Ya tenés un entrenador o una solicitud pendiente"
        )
    return trainer_service.mi_vinculo(db, usuario.id)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def finalizar(usuario: Usuario = Depends(solo_usuario), db: Session = Depends(get_db)):
    try:
        vinculo_service.finalizar_como_cliente(db, usuario)
    except vinculo_service.VinculoNoEncontrado:
        raise HTTPException(status_code=404, detail="No tenés una relación vigente con un entrenador")
    return Response(status_code=status.HTTP_204_NO_CONTENT)