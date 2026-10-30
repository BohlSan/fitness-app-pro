from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_role
from app.models.usuario import RolUsuario, Usuario
from app.schemas.estadisticas import EvolucionPesoOut, PesoIn
from app.services import peso_service

router = APIRouter(prefix="/peso", tags=["Peso corporal"])

solo_usuario = require_role(RolUsuario.USUARIO)


@router.get("", response_model=EvolucionPesoOut)
def evolucion(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    return peso_service.obtener_evolucion(db, usuario.id, desde, hasta)


@router.post("", response_model=EvolucionPesoOut, status_code=status.HTTP_201_CREATED)
def registrar(
    datos: PesoIn,
    usuario: Usuario = Depends(solo_usuario),
    db: Session = Depends(get_db),
):
    try:
        peso_service.registrar_peso(db, usuario, datos.peso_kg, datos.fecha)
    except peso_service.PerfilIncompleto:
        raise HTTPException(
            status_code=409, detail="Completá tu perfil antes de registrar tu peso"
        )
    except peso_service.DatosPesoInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))
    return peso_service.obtener_evolucion(db, usuario.id)