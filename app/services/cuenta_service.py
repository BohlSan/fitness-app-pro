from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.ejercicio import Ejercicio
from app.models.entrenamiento import EjercicioEntrenamiento, Entrenamiento
from app.models.rutina import Rutina, RutinaEjercicio
from app.models.usuario import Usuario
from app.schemas.cuenta import CambioPasswordIn, CuentaUpdate
from app.security import hash_password, verify_password
from app.services import auditoria_service
from app.services.auth_service import EmailYaRegistrado  # noqa: F401  (se reutiliza)


class PasswordIncorrecta(Exception):
    pass


def actualizar_datos(db: Session, usuario: Usuario, datos: CuentaUpdate) -> Usuario:
    # Primero se valida todo y recién después se modifica (RNF-14)
    nuevo_email = None
    if datos.email is not None:
        candidato = datos.email.strip().lower()
        if candidato != usuario.email:
            if not datos.password_actual or not verify_password(
                datos.password_actual, usuario.password_hash
            ):
                raise PasswordIncorrecta()
            en_uso = db.scalar(
                select(Usuario.id).where(Usuario.email == candidato, Usuario.id != usuario.id)
            )
            if en_uso is not None:
                raise EmailYaRegistrado()
            nuevo_email = candidato

    if datos.nombre is not None:
        usuario.nombre = datos.nombre
    if nuevo_email is not None:
        usuario.email = nuevo_email

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise EmailYaRegistrado()
    db.refresh(usuario)
    return usuario


def cambiar_password(db: Session, usuario: Usuario, datos: CambioPasswordIn) -> None:
    if not verify_password(datos.password_actual, usuario.password_hash):
        raise PasswordIncorrecta()
    usuario.password_hash = hash_password(datos.password_nueva)
    auditoria_service.registrar(db, usuario, "CAMBIAR_PASSWORD", "usuario", usuario.id)
    db.commit()


def eliminar_cuenta(db: Session, usuario: Usuario) -> None:
    """Borra la cuenta y los datos de la persona, en una sola transacción.

    - Sus rutinas y entrenamientos se borran (y con ellos sus días, series, etc.).
    - Sus ejercicios propios sin uso se borran. Los que todavía están en rutinas o
      entrenamientos de otras personas (por ejemplo, rutinas que armó para sus clientes)
      quedan en el catálogo, sin autor.
    - Las rutinas que armó para otras personas siguen siendo de ellas (sin autor).
    - La relación con su trainer o con sus clientes, los pagos y las novedades se
      eliminan por las claves foráneas (ON DELETE CASCADE).
    """
    usuario_id = usuario.id

    # El registro de auditoría se inserta ahora, mientras la cuenta todavía existe;
    # después queda sin usuario (ON DELETE SET NULL)
    auditoria_service.registrar(db, usuario, "ELIMINAR_CUENTA", "usuario", usuario_id)
    db.flush()

    db.execute(
        delete(Rutina).where(Rutina.propietario_id == usuario_id).execution_options(synchronize_session=False)
    )
    db.execute(
        delete(Entrenamiento)
        .where(Entrenamiento.usuario_id == usuario_id)
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(Ejercicio)
        .where(
            Ejercicio.creador_id == usuario_id,
            Ejercicio.id.not_in(select(RutinaEjercicio.ejercicio_id)),
            Ejercicio.id.not_in(select(EjercicioEntrenamiento.ejercicio_id)),
        )
        .execution_options(synchronize_session=False)
    )
    db.execute(
        delete(Usuario).where(Usuario.id == usuario_id).execution_options(synchronize_session=False)
    )
    db.commit()