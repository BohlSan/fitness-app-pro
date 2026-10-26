from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.ejercicio import ETIQUETAS_GRUPO_MUSCULAR, GrupoMuscular
from app.models.usuario import Usuario
from app.schemas.ejercicio import (
    EjercicioCreate,
    EjercicioOut,
    EjercicioUpdate,
    GrupoOut,
)
from app.services import ejercicio_service

router = APIRouter(prefix="/ejercicios", tags=["Ejercicios"])


# Debe declararse antes de "/{ejercicio_id}"
@router.get("/grupos", response_model=list[GrupoOut])
def listar_grupos(usuario: Usuario = Depends(get_current_user)):
    return [
        GrupoOut(valor=grupo.value, etiqueta=ETIQUETAS_GRUPO_MUSCULAR[grupo])
        for grupo in GrupoMuscular
    ]


@router.get("", response_model=list[EjercicioOut])
def listar(
    grupo: GrupoMuscular | None = None,
    q: str | None = Query(default=None, max_length=100),
    solo_propios: bool = False,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ejercicio_service.listar_ejercicios(db, usuario, grupo, q, solo_propios)


@router.get("/{ejercicio_id}", response_model=EjercicioOut)
def obtener(
    ejercicio_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ejercicio_service.obtener_ejercicio(db, usuario, ejercicio_id)
    except ejercicio_service.EjercicioNoEncontrado:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")


@router.post("", response_model=EjercicioOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: EjercicioCreate,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ejercicio_service.crear_ejercicio_personal(db, usuario, datos)
    except ejercicio_service.NombreDuplicado:
        raise HTTPException(status_code=409, detail="Ya existe un ejercicio con ese nombre")


@router.patch("/{ejercicio_id}", response_model=EjercicioOut)
def actualizar(
    ejercicio_id: int,
    cambios: EjercicioUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return ejercicio_service.actualizar_ejercicio(db, usuario, ejercicio_id, cambios)
    except ejercicio_service.EjercicioNoEncontrado:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    except ejercicio_service.EjercicioNoModificable:
        raise HTTPException(
            status_code=403,
            detail="Los ejercicios del catálogo no se pueden modificar",
        )
    except ejercicio_service.NombreDuplicado:
        raise HTTPException(status_code=409, detail="Ya existe un ejercicio con ese nombre")
    except ejercicio_service.DatosEjercicioInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))


@router.delete("/{ejercicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    ejercicio_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        ejercicio_service.eliminar_ejercicio(db, usuario, ejercicio_id)
    except ejercicio_service.EjercicioNoEncontrado:
        raise HTTPException(status_code=404, detail="Ejercicio no encontrado")
    except ejercicio_service.EjercicioNoModificable:
        raise HTTPException(
            status_code=403,
            detail="Los ejercicios del catálogo no se pueden eliminar",
        )
    except ejercicio_service.EjercicioEnUso:
        raise HTTPException(
            status_code=409,
            detail="No se puede eliminar: el ejercicio está en una rutina o en un entrenamiento",
            )
    return Response(status_code=status.HTTP_204_NO_CONTENT)