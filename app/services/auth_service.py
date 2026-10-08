from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.usuario import Usuario
from app.schemas.auth import RegistroIn
from app.security import hash_password, verify_password


class EmailYaRegistrado(Exception):
    pass


class CredencialesInvalidas(Exception):
    pass


def registrar_usuario(db: Session, datos: RegistroIn) -> Usuario:
    email = datos.email.strip().lower()
    if db.scalar(select(Usuario).where(Usuario.email == email)):
        raise EmailYaRegistrado()

    usuario = Usuario(
        nombre=datos.nombre,
        email=email,
        password_hash=hash_password(datos.password),
        rol=datos.rol,
    )
    db.add(usuario)
    try:
        db.commit()
    except IntegrityError:
        # RNF-14: dos registros simultáneos con el mismo email
        db.rollback()
        raise EmailYaRegistrado()
    db.refresh(usuario)
    return usuario


def autenticar_usuario(db: Session, email: str, password: str) -> Usuario:
    usuario = db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))
    # Mismo error para "no existe" y "contraseña incorrecta" (RNF-13)
    if usuario is None or not verify_password(password, usuario.password_hash):
        raise CredencialesInvalidas()
    return usuario