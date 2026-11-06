from sqlalchemy import select

import app.models  # noqa: F401  (registra los modelos en la metadata)
from app.database import SessionLocal
from app.models.ejercicio import Ejercicio, GrupoMuscular as G, TipoMedicion
from app.models.entrenamiento import EjercicioEntrenamiento
from app.models.rutina import RutinaEjercicio
from app.schemas.ejercicio import EjercicioCreate
from app.services.ejercicio_factory import EjercicioFactory

# (nombre, grupo principal, grupo secundario, descripción)
EJERCICIOS_PESO_CORPORAL = {
    "Flexiones de brazos",
    "Fondos en paralelas",
    "Dominadas",
    "Fondos en banco",
}

# El catálogo inicial marca como temporizados los ejercicios de cardio.
# Los isométricos también pueden crearse por tiempo desde la interfaz.
EJERCICIOS_POR_TIEMPO = {"Cinta de correr", "Bicicleta fija", "Saltar la cuerda"}


def _esta_en_uso(db, ejercicio_id: int) -> bool:
    """No cambia la semántica de ejercicios que ya tienen rutinas o historial."""
    en_rutina = db.scalar(
        select(RutinaEjercicio.id)
        .where(RutinaEjercicio.ejercicio_id == ejercicio_id)
        .limit(1)
    )
    en_historial = db.scalar(
        select(EjercicioEntrenamiento.id)
        .where(EjercicioEntrenamiento.ejercicio_id == ejercicio_id)
        .limit(1)
    )
    return en_rutina is not None or en_historial is not None


def _crear_o_actualizar_variante(
    db,
    existentes: dict[str, Ejercicio],
    ejercicio: Ejercicio,
    nombre: str,
    tipo: TipoMedicion,
    usa_peso: bool,
) -> bool:
    """Crea la variante nueva o sincroniza una ya sembrada. Devuelve True si la creó."""
    variante = existentes.get(nombre)
    if variante is None:
        datos = EjercicioCreate(
            nombre=nombre,
            descripcion=ejercicio.descripcion,
            grupo_principal=ejercicio.grupo_principal,
            grupo_secundario=ejercicio.grupo_secundario,
            tipo_medicion=tipo,
            usa_peso_corporal=usa_peso,
        )
        variante = EjercicioFactory.crear_base(datos)
        db.add(variante)
        existentes[nombre] = variante
        return True

    variante.tipo_medicion = tipo
    variante.usa_peso_corporal = usa_peso
    return False


CATALOGO = [
    # Pecho
    ("Press de banca plano", G.PECHO, G.TRICEPS, "Acostado en el banco, bajá la barra hasta el pecho y empujala hacia arriba."),
    ("Press inclinado con mancuernas", G.PECHO, G.HOMBROS, "En banco inclinado, empujá las mancuernas hacia arriba juntando los brazos."),
    ("Aperturas con mancuernas", G.PECHO, None, "Acostado, abrí los brazos en arco y volvé a juntar las mancuernas sobre el pecho."),
    ("Flexiones de brazos", G.PECHO, G.TRICEPS, "Con el cuerpo en línea recta, bajá el pecho al piso y empujá hacia arriba."),
    ("Fondos en paralelas", G.PECHO, G.TRICEPS, "Suspendido en barras paralelas, bajá flexionando los codos y subí empujando."),
    # Espalda
    ("Dominadas", G.ESPALDA, G.BICEPS, "Colgado de la barra, llevá el mentón por encima de ella tirando con la espalda."),
    ("Remo con barra", G.ESPALDA, G.BICEPS, "Con el torso inclinado, tirá la barra hacia el abdomen con la espalda recta."),
    ("Jalón al pecho", G.ESPALDA, G.BICEPS, "Sentado en la polea, tirá la barra hacia el pecho sin balancear el torso."),
    ("Remo en polea baja", G.ESPALDA, G.BICEPS, "Sentado, tirá del agarre hacia el abdomen juntando los omóplatos."),
    ("Remo con mancuerna a una mano", G.ESPALDA, G.BICEPS, "Apoyado en un banco, tirá la mancuerna hacia la cadera."),
    ("Peso muerto", G.ESPALDA, G.GLUTEOS, "Levantá la barra del piso con la espalda recta hasta quedar de pie."),
    # Hombros
    ("Press militar con barra", G.HOMBROS, G.TRICEPS, "De pie, empujá la barra desde los hombros hasta estirar los brazos arriba."),
    ("Press de hombros con mancuernas", G.HOMBROS, G.TRICEPS, "Sentado, empujá las mancuernas por encima de la cabeza."),
    ("Elevaciones laterales", G.HOMBROS, None, "Con mancuernas, elevá los brazos a los costados hasta la altura de los hombros."),
    ("Pájaros con mancuernas", G.HOMBROS, G.ESPALDA, "Inclinado hacia adelante, abrí los brazos hacia atrás con mancuernas."),
    # Bíceps
    ("Curl de bíceps con barra", G.BICEPS, None, "De pie, flexioná los codos subiendo la barra sin balancear el cuerpo."),
    ("Curl martillo con mancuernas", G.BICEPS, None, "Con las palmas enfrentadas, flexioná los codos subiendo las mancuernas."),
    ("Curl en banco inclinado", G.BICEPS, None, "Sentado en banco inclinado, flexioná los codos con los brazos colgando atrás."),
    # Tríceps
    ("Extensión de tríceps en polea", G.TRICEPS, None, "De pie frente a la polea, empujá el agarre hacia abajo extendiendo los codos."),
    ("Press francés", G.TRICEPS, None, "Acostado, flexioná los codos bajando la barra hacia la frente y extendé."),
    ("Fondos en banco", G.TRICEPS, G.HOMBROS, "Con las manos apoyadas en un banco, bajá y subí flexionando los codos."),
    # Cuádriceps
    ("Sentadilla con barra", G.CUADRICEPS, G.GLUTEOS, "Con la barra en la espalda, bajá flexionando rodillas y cadera y volvé a subir."),
    ("Prensa de piernas", G.CUADRICEPS, G.GLUTEOS, "Sentado en la máquina, empujá la plataforma con las piernas."),
    ("Extensión de cuádriceps", G.CUADRICEPS, None, "Sentado en la máquina, extendé las rodillas levantando el peso."),
    ("Zancadas con mancuernas", G.CUADRICEPS, G.GLUTEOS, "Dá un paso largo al frente y bajá la rodilla trasera hacia el piso."),
    ("Sentadilla búlgara", G.CUADRICEPS, G.GLUTEOS, "Con un pie apoyado atrás en un banco, bajá y subí con la pierna de adelante."),
    # Isquiotibiales
    ("Peso muerto rumano", G.ISQUIOTIBIALES, G.GLUTEOS, "Con las piernas casi rectas, llevá la cadera atrás y bajá la barra por los muslos."),
    ("Curl femoral acostado", G.ISQUIOTIBIALES, None, "Boca abajo en la máquina, flexioná las rodillas llevando los talones a los glúteos."),
    ("Curl femoral sentado", G.ISQUIOTIBIALES, None, "Sentado en la máquina, flexioná las rodillas empujando el rodillo hacia abajo."),
    # Glúteos
    ("Hip thrust", G.GLUTEOS, G.ISQUIOTIBIALES, "Con la espalda apoyada en un banco, elevá la cadera con la barra encima."),
    ("Puente de glúteos", G.GLUTEOS, G.ISQUIOTIBIALES, "Acostado boca arriba, elevá la cadera apretando los glúteos."),
    ("Patada de glúteo en polea", G.GLUTEOS, None, "Con el tobillo enganchado a la polea, llevá la pierna hacia atrás."),
    # Pantorrillas
    ("Elevación de talones de pie", G.PANTORRILLAS, None, "De pie, subí sobre las puntas de los pies y bajá controlando."),
    ("Elevación de talones sentado", G.PANTORRILLAS, None, "Sentado con el peso sobre las rodillas, subí y bajá los talones."),
    # Abdominales
    ("Plancha abdominal", G.ABDOMINALES, None, "Apoyado en antebrazos y puntas de pie, mantené el cuerpo recto."),
    ("Crunch abdominal", G.ABDOMINALES, None, "Acostado, flexioná el tronco llevando los hombros hacia las rodillas."),
    ("Elevación de piernas colgado", G.ABDOMINALES, None, "Colgado de la barra, subí las piernas rectas hasta la altura de la cadera."),
    ("Rueda abdominal", G.ABDOMINALES, G.HOMBROS, "De rodillas, rodá la rueda hacia adelante y volvé contrayendo el abdomen."),
    # Cuerpo completo
    ("Burpees", G.CUERPO_COMPLETO, G.CARDIO, "Flexión en el piso seguida de un salto, repetida de forma continua."),
    ("Kettlebell swing", G.CUERPO_COMPLETO, G.GLUTEOS, "Balanceá la pesa desde entre las piernas hasta la altura del pecho con la cadera."),
    # Cardio
    ("Cinta de correr", G.CARDIO, None, "Caminá o corré a ritmo constante o por intervalos."),
    ("Bicicleta fija", G.CARDIO, G.CUADRICEPS, "Pedaleá a ritmo constante o por intervalos."),
    ("Saltar la cuerda", G.CARDIO, G.PANTORRILLAS, "Saltá de forma continua pasando la cuerda por debajo de los pies."),
]


def main():
    with SessionLocal() as db:
        existentes = {
            nombre.lower()
            for nombre in db.scalars(
                select(Ejercicio.nombre).where(Ejercicio.creador_id.is_(None))
            )
        }
        nuevos = 0
        for nombre, principal, secundario, descripcion in CATALOGO:
            if nombre.lower() in existentes:
                continue
            datos = EjercicioCreate(
                nombre=nombre,
                descripcion=descripcion,
                grupo_principal=principal,
                grupo_secundario=secundario,
                tipo_medicion=(
                    TipoMedicion.TIEMPO
                    if nombre in EJERCICIOS_POR_TIEMPO
                    else TipoMedicion.REPETICIONES
                ),
                usa_peso_corporal=nombre in EJERCICIOS_PESO_CORPORAL,
            )
            db.add(EjercicioFactory.crear_base(datos))
            nuevos += 1
        # Sincroniza los ejercicios especiales ya existentes sin reinterpretar su historial.
        existentes_por_nombre = {
            ejercicio.nombre: ejercicio
            for ejercicio in db.scalars(
                select(Ejercicio).where(Ejercicio.creador_id.is_(None))
            )
        }
        for nombre in EJERCICIOS_POR_TIEMPO | EJERCICIOS_PESO_CORPORAL:
            ejercicio = existentes_por_nombre.get(nombre)
            if ejercicio is None:
                continue
            tipo_deseado = (
                TipoMedicion.TIEMPO
                if nombre in EJERCICIOS_POR_TIEMPO
                else TipoMedicion.REPETICIONES
            )
            peso_deseado = nombre in EJERCICIOS_PESO_CORPORAL
            cambia_tipo = ejercicio.tipo_medicion != tipo_deseado
            cambia_peso = ejercicio.usa_peso_corporal != peso_deseado

            if (cambia_tipo or cambia_peso) and _esta_en_uso(db, ejercicio.id):
                sufijo = "por tiempo" if tipo_deseado == TipoMedicion.TIEMPO else "peso corporal"
                nombre_variante = f"{nombre} ({sufijo})"
                creados = _crear_o_actualizar_variante(
                    db,
                    existentes_por_nombre,
                    ejercicio,
                    nombre_variante,
                    tipo_deseado,
                    peso_deseado,
                )
                nuevos += int(creados)
                continue

            ejercicio.tipo_medicion = tipo_deseado
            ejercicio.usa_peso_corporal = peso_deseado

        db.commit()
    print(f"Catálogo listo: {nuevos} ejercicios nuevos; tipos y cargas sincronizados sin alterar el historial.")


if __name__ == "__main__":
    main()