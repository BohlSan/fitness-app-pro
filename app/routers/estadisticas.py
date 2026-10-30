from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.estadisticas import (
    EjercicioEntrenadoOut,
    EvolucionEjercicioOut,
    PROut,
    ResumenOut,
)
from app.services import estadisticas_service

router = APIRouter(prefix="/estadisticas", tags=["Estadísticas"])

_PERIODO_INVALIDO = 'La fecha "desde" no puede ser posterior a "hasta"'
_SIN_REGISTROS = "No hay registros para consultar"


@router.get("/resumen", response_model=ResumenOut)
def resumen(
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return estadisticas_service.resumen(db, usuario.id, desde, hasta)
    except estadisticas_service.PeriodoInvalido:
        raise HTTPException(status_code=422, detail=_PERIODO_INVALIDO)


@router.get("/ejercicios", response_model=list[EjercicioEntrenadoOut])
def ejercicios_entrenados(
    usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)
):
    return estadisticas_service.ejercicios_entrenados(db, usuario.id)


@router.get("/ejercicios/{ejercicio_id}", response_model=EvolucionEjercicioOut)
def evolucion_ejercicio(
    ejercicio_id: int,
    desde: date | None = None,
    hasta: date | None = None,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return estadisticas_service.evolucion_ejercicio(db, usuario.id, ejercicio_id, desde, hasta)
    except estadisticas_service.PeriodoInvalido:
        raise HTTPException(status_code=422, detail=_PERIODO_INVALIDO)
    except estadisticas_service.SinRegistros:
        raise HTTPException(status_code=404, detail=_SIN_REGISTROS)


@router.get("/entrenamientos/{entrenamiento_id}/prs", response_model=list[PROut])
def prs_del_entrenamiento(
    entrenamiento_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return estadisticas_service.prs_de_entrenamiento(db, usuario.id, entrenamiento_id)
    except estadisticas_service.SinRegistros:
        raise HTTPException(status_code=404, detail=_SIN_REGISTROS)