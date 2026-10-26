from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.rutina import RutinaIn, RutinaOut
from app.services import rutina_service

router = APIRouter(prefix="/rutinas", tags=["Rutinas"])


def _no_encontrada() -> HTTPException:
    return HTTPException(status_code=404, detail="Rutina no encontrada")


@router.get("", response_model=list[RutinaOut])
def listar(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    rutinas = rutina_service.listar_rutinas(db, usuario)
    return [RutinaOut.model_validate(rutina) for rutina in rutinas]


@router.post("", response_model=RutinaOut, status_code=status.HTTP_201_CREATED)
def crear(
    datos: RutinaIn,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rutina = rutina_service.crear_rutina(db, usuario, datos)
    except rutina_service.DatosRutinaInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))
    return RutinaOut.model_validate(rutina)


@router.get("/{rutina_id}", response_model=RutinaOut)
def obtener(
    rutina_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rutina = rutina_service.obtener_rutina(db, usuario, rutina_id)
    except rutina_service.RutinaNoEncontrada:
        raise _no_encontrada()
    return RutinaOut.model_validate(rutina)


@router.put("/{rutina_id}", response_model=RutinaOut)
def actualizar(
    rutina_id: int,
    datos: RutinaIn,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rutina = rutina_service.actualizar_rutina(db, usuario, rutina_id, datos)
    except rutina_service.RutinaNoEncontrada:
        raise _no_encontrada()
    except rutina_service.DatosRutinaInvalidos as error:
        raise HTTPException(status_code=422, detail=str(error))
    return RutinaOut.model_validate(rutina)


@router.delete("/{rutina_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(
    rutina_id: int,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        rutina_service.eliminar_rutina(db, usuario, rutina_id)
    except rutina_service.RutinaNoEncontrada:
        raise _no_encontrada()
    return Response(status_code=status.HTTP_204_NO_CONTENT)