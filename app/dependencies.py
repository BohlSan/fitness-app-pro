import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import RolUsuario, Usuario
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _no_autenticado(detalle: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credenciales: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    if credenciales is None:
        raise _no_autenticado("No autenticado")
    try:
        payload = decode_token(credenciales.credentials)
        usuario_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise _no_autenticado("Sesión inválida o expirada")

    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise _no_autenticado("Sesión inválida o expirada")
    return usuario


def require_role(*roles: RolUsuario):
    def verificar(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenés permisos para esta acción",
            )
        return usuario

    return verificar