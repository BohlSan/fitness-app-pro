from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import UsuarioOut
from app.schemas.cuenta import CambioPasswordIn, CuentaUpdate, EliminarCuentaIn
from app.services import cuenta_service

router = APIRouter(prefix="/cuenta", tags=["Cuenta"])

_PASSWORD_INCORRECTA = "La contraseña actual no es correcta"


@router.patch("/datos", response_model=UsuarioOut)
def actualizar_datos(
    datos: CuentaUpdate,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return cuenta_service.actualizar_datos(db, usuario, datos)
    except cuenta_service.PasswordIncorrecta:
        raise HTTPException(status_code=403, detail=_PASSWORD_INCORRECTA)
    except cuenta_service.EmailYaRegistrado:
        raise HTTPException(status_code=409, detail="El email ya está registrado")


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_password(
    datos: CambioPasswordIn,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        cuenta_service.cambiar_password(db, usuario, datos)
    except cuenta_service.PasswordIncorrecta:
        raise HTTPException(status_code=403, detail=_PASSWORD_INCORRECTA)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/eliminar", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuenta(
    datos: EliminarCuentaIn,  # la confirmación se valida en el esquema
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cuenta_service.eliminar_cuenta(db, usuario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)