from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.entrenamiento import (
    DiaCalendarioOut,
    EntrenamientoOut,
    EntrenamientoStart,
    EntrenamientoSync,
    FinalizarIn,
)
from app.services import entrenamiento_service, historial_service, rutina_service

router = APIRouter(prefix="/entrenamientos", tags=["Entrenamientos"])


def _no_encontrado() -> HTTPException:
    return HTTPException(status_code=404, detail="Entrenamiento no encontrado")


def _ya_finalizado() -> HTTPException:
    return HTTPException(status_code=409, detail="El entrenamiento ya fue finalizado")


# Debe declararse antes de "/{entrenamiento_id}"
@router.get("/en-curso", response_model=EntrenamientoOut | None)
def en_curso(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    entrenamiento = entrenamiento_service.obtener_en_curso(db, usuario)
    if entrenamiento is None:
        return None
    return EntrenamientoOut.model_validate(entrenamiento)


@router.get("", response_model=list[EntrenamientoOut])
def historial(
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        entrenamientos = historial_service.listar_historial(
            db, usuario.id, desde, hasta, limite, offset
        )
    except historial_service.PeriodoInvalido:
        raise HTTPException(
            status_code=422,
            detail='La fecha "desde" no puede ser posterior a "hasta"',
        )
    return [EntrenamientoOut.model_validate(e) for e in entrenamientos]


@router.get("/calendario", response_model=list[DiaCalendarioOut])
def calendario(
    anio: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return historial_service.calendario_mensual(db, usuario.id, anio, mes)


@router.post("", response_model=EntrenamientoOut, status_code=status.HTTP_201_CREATED)
def iniciar(
    datos: EntrenamientoStart,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        entrenamiento = entrenamiento_service.iniciar_entrenamiento(db, usuario, datos)
    except entrenamiento_service.EntrenamientoEnCurso:
        raise HTTPException(status_code=409, detail="Ya tenés un entrenamiento en curso")
    except rutina_service.RutinaNoEncontrada:
        raise HTTPException(status_code=404, detail="Rutina no encontrada")
    except entrenamiento_service.DatosEntrenamientoInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))
    return EntrenamientoOut.model_validate(entrenamiento)


@router.get("/{entrenamiento_id}", response_model=EntrenamientoOut)
def obtener(
    entrenamiento_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        entrenamiento = entrenamiento_service.obtener_entrenamiento(db, usuario, entrenamiento_id)
    except entrenamiento_service.EntrenamientoNoEncontrado:
        raise _no_encontrado()
    return EntrenamientoOut.model_validate(entrenamiento)


@router.put("/{entrenamiento_id}", response_model=EntrenamientoOut)
def actualizar(
    entrenamiento_id: int,
    datos: EntrenamientoSync,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        entrenamiento = entrenamiento_service.actualizar_entrenamiento(
            db, usuario, entrenamiento_id, datos
        )
    except entrenamiento_service.EntrenamientoNoEncontrado:
        raise _no_encontrado()
    except entrenamiento_service.EntrenamientoNoEditable:
        raise _ya_finalizado()
    except entrenamiento_service.DatosEntrenamientoInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))
    return EntrenamientoOut.model_validate(entrenamiento)


@router.post("/{entrenamiento_id}/finalizar", response_model=EntrenamientoOut)
def finalizar(
    entrenamiento_id: int,
    datos: FinalizarIn,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        entrenamiento = entrenamiento_service.finalizar_entrenamiento(
            db, usuario, entrenamiento_id, datos
        )
    except entrenamiento_service.EntrenamientoNoEncontrado:
        raise _no_encontrado()
    except entrenamiento_service.EntrenamientoNoEditable:
        raise _ya_finalizado()
    except entrenamiento_service.DatosEntrenamientoInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))
    return EntrenamientoOut.model_validate(entrenamiento)


@router.delete("/{entrenamiento_id}", status_code=status.HTTP_204_NO_CONTENT)
def descartar(
    entrenamiento_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        entrenamiento_service.descartar_entrenamiento(db, usuario, entrenamiento_id)
    except entrenamiento_service.EntrenamientoNoEncontrado:
        raise _no_encontrado()
    except entrenamiento_service.EntrenamientoNoEditable:
        raise HTTPException(
            status_code=409,
            detail="Un entrenamiento finalizado no se puede eliminar",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)