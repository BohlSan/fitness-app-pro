from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.ejercicio import Ejercicio, GrupoMuscular
from app.models.entrenamiento import EjercicioEntrenamiento
from app.models.rutina import RutinaEjercicio
from app.models.usuario import Usuario
from app.schemas.ejercicio import EjercicioCreate, EjercicioUpdate
from app.services.ejercicio_factory import EjercicioFactory


class EjercicioNoEncontrado(Exception):
    pass


class EjercicioNoModificable(Exception):
    pass


class NombreDuplicado(Exception):
    pass


class DatosEjercicioInvalidos(Exception):
    pass


class EjercicioEnUso(Exception):
    pass

def _visibles(usuario: Usuario):
    """Catálogo base + ejercicios propios."""
    return or_(Ejercicio.creador_id.is_(None), Ejercicio.creador_id == usuario.id)


def _verificar_nombre_libre(
    db: Session, usuario: Usuario, nombre: str, excluir_id: int | None = None
) -> None:
    consulta = select(Ejercicio.id).where(
        func.lower(Ejercicio.nombre) == nombre.lower(), _visibles(usuario)
    )
    if excluir_id is not None:
        consulta = consulta.where(Ejercicio.id != excluir_id)
    if db.scalar(consulta) is not None:
        raise NombreDuplicado()


def listar_ejercicios(
    db: Session,
    usuario: Usuario,
    grupo: GrupoMuscular | None = None,
    texto: str | None = None,
    solo_propios: bool = False,
) -> list[Ejercicio]:
    consulta = select(Ejercicio)
    if solo_propios:
        consulta = consulta.where(Ejercicio.creador_id == usuario.id)
    else:
        consulta = consulta.where(_visibles(usuario))
    if grupo is not None:
        consulta = consulta.where(Ejercicio.grupo_principal == grupo)
    if texto and texto.strip():
        consulta = consulta.where(
            Ejercicio.nombre.icontains(texto.strip(), autoescape=True)
        )
    consulta = consulta.order_by(func.lower(Ejercicio.nombre))
    return list(db.scalars(consulta))


def obtener_ejercicio(db: Session, usuario: Usuario, ejercicio_id: int) -> Ejercicio:
    ejercicio = db.scalar(
        select(Ejercicio).where(Ejercicio.id == ejercicio_id, _visibles(usuario))
    )
    # El ejercicio personal de otra persona se trata como inexistente (RNF-15)
    if ejercicio is None:
        raise EjercicioNoEncontrado()
    return ejercicio


def crear_ejercicio_personal(
    db: Session, usuario: Usuario, datos: EjercicioCreate
) -> Ejercicio:
    _verificar_nombre_libre(db, usuario, datos.nombre)
    ejercicio = EjercicioFactory.crear_personal(datos, usuario)
    db.add(ejercicio)
    db.commit()
    db.refresh(ejercicio)
    return ejercicio


def _exigir_propio(ejercicio: Ejercicio, usuario: Usuario) -> None:
    if ejercicio.creador_id != usuario.id:
        raise EjercicioNoModificable()


def actualizar_ejercicio(
    db: Session, usuario: Usuario, ejercicio_id: int, cambios: EjercicioUpdate
) -> Ejercicio:
    ejercicio = obtener_ejercicio(db, usuario, ejercicio_id)
    _exigir_propio(ejercicio, usuario)

    for campo, valor in cambios.model_dump(exclude_unset=True).items():
        # nombre y grupo principal no admiten null; los otros dos sí (para borrarlos)
        if valor is None and campo in ("nombre", "grupo_principal"):
            continue
        setattr(ejercicio, campo, valor)

    try:
        if (
            ejercicio.grupo_secundario is not None
            and ejercicio.grupo_secundario == ejercicio.grupo_principal
        ):
            raise DatosEjercicioInvalidos(
                "El grupo secundario debe ser distinto del principal"
            )
        _verificar_nombre_libre(db, usuario, ejercicio.nombre, excluir_id=ejercicio.id)
    except (DatosEjercicioInvalidos, NombreDuplicado):
        db.rollback()  # RNF-14: no dejar cambios a medias
        raise

    db.commit()
    db.refresh(ejercicio)
    return ejercicio


def eliminar_ejercicio(db: Session, usuario: Usuario, ejercicio_id: int) -> None:
    ejercicio = obtener_ejercicio(db, usuario, ejercicio_id)
    _exigir_propio(ejercicio, usuario)

    en_rutina = db.scalar(
        select(RutinaEjercicio.id)
        .where(RutinaEjercicio.ejercicio_id == ejercicio.id)
        .limit(1)
    )
    en_historial = db.scalar(
        select(EjercicioEntrenamiento.id)
        .where(EjercicioEntrenamiento.ejercicio_id == ejercicio.id)
        .limit(1)
    )
    if en_rutina is not None or en_historial is not None:
        raise EjercicioEnUso()

    db.delete(ejercicio)
    db.commit()


def ids_ejercicios_visibles(db: Session, usuario: Usuario, ids: set[int]) -> set[int]:
    """De los ids pedidos, devuelve los que la persona puede usar (catálogo o propios)."""
    if not ids:
        return set()
    consulta = select(Ejercicio.id).where(Ejercicio.id.in_(list(ids)), _visibles(usuario))
    return set(db.scalars(consulta))