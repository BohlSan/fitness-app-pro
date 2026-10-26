from app.models.ejercicio import Ejercicio
from app.models.usuario import Usuario
from app.schemas.ejercicio import EjercicioCreate


class EjercicioFactory:
    """Centraliza cómo se construye cada tipo de ejercicio (RNF-06).

    Para sumar un tipo nuevo (por ejemplo, ejercicios premium) se agrega un
    método acá, sin tocar a quienes ya usan la fábrica.
    """

    @staticmethod
    def _construir(datos: EjercicioCreate, creador_id: int | None) -> Ejercicio:
        return Ejercicio(
            nombre=datos.nombre,
            descripcion=datos.descripcion,
            grupo_principal=datos.grupo_principal,
            grupo_secundario=datos.grupo_secundario,
            creador_id=creador_id,
        )

    @staticmethod
    def crear_base(datos: EjercicioCreate) -> Ejercicio:
        """Ejercicio del catálogo: sin creador, de solo lectura para todos."""
        return EjercicioFactory._construir(datos, creador_id=None)

    @staticmethod
    def crear_personal(datos: EjercicioCreate, creador: Usuario) -> Ejercicio:
        """Ejercicio propio: pertenece a quien lo creó."""
        return EjercicioFactory._construir(datos, creador_id=creador.id)