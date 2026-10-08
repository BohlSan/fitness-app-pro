from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.usuario import Usuario
from app.schemas.auth import AuthOut, LoginIn, RegistroIn, UsuarioOut
from app.security import create_access_token
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Autenticación"])


def _respuesta_auth(usuario: Usuario) -> AuthOut:
    return AuthOut(
        access_token=create_access_token(usuario.id),
        usuario=UsuarioOut.model_validate(usuario),
    )


@router.post("/registro", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def registro(datos: RegistroIn, db: Session = Depends(get_db)):
    try:
        usuario = auth_service.registrar_usuario(db, datos)
    except auth_service.EmailYaRegistrado:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya está registrado",
        )
    return _respuesta_auth(usuario)


@router.post("/login", response_model=AuthOut)
def login(datos: LoginIn, db: Session = Depends(get_db)):
    try:
        usuario = auth_service.autenticar_usuario(db, datos.email, datos.password)
    except auth_service.CredencialesInvalidas:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    return _respuesta_auth(usuario)


@router.get("/me", response_model=UsuarioOut)
def me(usuario: Usuario = Depends(get_current_user)):
    return usuario