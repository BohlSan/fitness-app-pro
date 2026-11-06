from collections import Counter, namedtuple
from datetime import date, timedelta

# Un registro realizado. Los campos nuevos tienen default para conservar compatibilidad
# con los tests y llamadas que todavía construyen filas de fuerza con cuatro argumentos.
FilaSerie = namedtuple(
    "FilaSerie",
    "entrenamiento_id fecha peso_kg repeticiones duracion_segundos tipo_medicion",
    defaults=[None, None],
)

# Por debajo de este cambio semanal, el peso se considera estable
UMBRAL_TENDENCIA_ESTABLE_KG_SEMANA = 0.1


def volumen_serie(peso_kg: float | None, repeticiones: int | None) -> float:
    if repeticiones is None:
        return 0.0  # Los registros por tiempo no generan volumen de fuerza.
    return float(peso_kg or 0) * repeticiones


def volumen_series(series) -> float:
    """Volumen = Σ (peso × repeticiones) de registros completados (RF-23).

    El peso corporal ya se guarda como peso_kg en cada serie. Los ejercicios por
    tiempo no tienen repeticiones y, por lo tanto, no suman volumen.
    """
    return sum(volumen_serie(s.peso_kg, s.repeticiones) for s in series if s.completada)


def _peso(fila) -> float:
    return float(fila.peso_kg or 0)


# ---------- Peso corporal (RF-22) ----------
def calcular_tendencia(puntos: list[tuple[date, float]]) -> dict | None:
    """Recta de mínimos cuadrados sobre (fecha, peso). Necesita 2 días distintos."""
    if len(puntos) < 2:
        return None
    base = puntos[0][0]
    xs = [(fecha - base).days for fecha, _ in puntos]
    if len(set(xs)) < 2:
        return None
    ys = [peso for _, peso in puntos]

    n = len(xs)
    media_x = sum(xs) / n
    media_y = sum(ys) / n
    sxx = sum((x - media_x) ** 2 for x in xs)
    sxy = sum((x - media_x) * (y - media_y) for x, y in zip(xs, ys))
    pendiente = sxy / sxx  # kg por día
    intercepto = media_y - pendiente * media_x

    semanal = pendiente * 7
    if abs(semanal) < UMBRAL_TENDENCIA_ESTABLE_KG_SEMANA:
        direccion = "ESTABLE"
    elif semanal < 0:
        direccion = "BAJA"
    else:
        direccion = "SUBE"

    return {
        "pendiente_kg_semana": round(semanal, 2),
        "direccion": direccion,
        "puntos": [
            {"fecha": fecha, "peso_kg": round(intercepto + pendiente * x, 2)}
            for (fecha, _), x in zip(puntos, xs)
        ],
    }


# ---------- Ejercicios (RF-23 y RF-24) ----------
def volumen_por_sesion(filas) -> list[dict]:
    """Agrupa las series de un ejercicio por entrenamiento, en orden cronológico."""
    sesiones: dict[int, dict] = {}
    for fila in sorted(filas, key=lambda f: (f.fecha, f.entrenamiento_id)):
        sesion = sesiones.setdefault(
            fila.entrenamiento_id,
            {
                "entrenamiento_id": fila.entrenamiento_id,
                "fecha": fila.fecha,
                "volumen_kg": 0.0,
                "peso_max_kg": 0.0,
                "series": 0,
                "repeticiones": 0,
                "duracion_total_segundos": 0,
            },
        )
        sesion["volumen_kg"] += volumen_serie(fila.peso_kg, fila.repeticiones)
        sesion["peso_max_kg"] = max(sesion["peso_max_kg"], _peso(fila))
        sesion["series"] += 1
        sesion["repeticiones"] += fila.repeticiones or 0
        sesion["duracion_total_segundos"] += fila.duracion_segundos or 0

    resultado = list(sesiones.values())
    for sesion in resultado:
        sesion["volumen_kg"] = round(sesion["volumen_kg"], 2)
    return resultado


def mejores_marcas(filas) -> dict:
    """Mejores marcas de un ejercicio. Ante empates se conserva la más antigua."""
    ordenadas = sorted(filas, key=lambda f: (f.fecha, f.entrenamiento_id))

    mayor_peso = None
    por_peso: dict[float, dict] = {}
    for fila in ordenadas:
        if fila.repeticiones is None:
            continue
        peso = _peso(fila)
        if peso > 0 and (
            mayor_peso is None
            or (peso, fila.repeticiones) > (mayor_peso["peso_kg"], mayor_peso["repeticiones"])
        ):
            mayor_peso = {
                "peso_kg": peso,
                "repeticiones": fila.repeticiones,
                "fecha": fila.fecha,
                "entrenamiento_id": fila.entrenamiento_id,
            }
        actual = por_peso.get(peso)
        if actual is None or fila.repeticiones > actual["repeticiones"]:
            por_peso[peso] = {"peso_kg": peso, "repeticiones": fila.repeticiones, "fecha": fila.fecha}

    mayor_duracion = None
    for fila in ordenadas:
        duracion = fila.duracion_segundos or 0
        if duracion > 0 and (mayor_duracion is None or duracion > mayor_duracion["duracion_segundos"]):
            mayor_duracion = {
                "duracion_segundos": duracion,
                "fecha": fila.fecha,
                "entrenamiento_id": fila.entrenamiento_id,
            }

    mejor_volumen = None
    for sesion in volumen_por_sesion(ordenadas):
        if sesion["volumen_kg"] > 0 and (
            mejor_volumen is None or sesion["volumen_kg"] > mejor_volumen["volumen_kg"]
        ):
            mejor_volumen = {
                "volumen_kg": sesion["volumen_kg"],
                "fecha": sesion["fecha"],
                "entrenamiento_id": sesion["entrenamiento_id"],
            }

    return {
        "mayor_peso": mayor_peso,
        "mayor_duracion": mayor_duracion,
        "mejor_volumen_sesion": mejor_volumen,
        "repeticiones_por_peso": sorted(por_peso.values(), key=lambda m: -m["peso_kg"]),
    }


def detectar_prs(previas, sesion) -> list[dict]:
    """Récords que una sesión rompió respecto de las sesiones anteriores del ejercicio."""
    if not previas or not sesion:
        return []

    marcas = mejores_marcas(previas)
    prs = []

    filas_fuerza = [f for f in sesion if f.repeticiones is not None]
    peso_max = max((_peso(f) for f in filas_fuerza), default=0)
    if marcas["mayor_peso"] and peso_max > marcas["mayor_peso"]["peso_kg"]:
        prs.append({"tipo": "PESO", "valor": peso_max, "anterior": marcas["mayor_peso"]["peso_kg"]})

    volumen = round(sum(_peso(f) * (f.repeticiones or 0) for f in filas_fuerza), 2)
    if marcas["mejor_volumen_sesion"] and volumen > marcas["mejor_volumen_sesion"]["volumen_kg"]:
        prs.append(
            {"tipo": "VOLUMEN", "valor": volumen, "anterior": marcas["mejor_volumen_sesion"]["volumen_kg"]}
        )

    reps_previas = {m["peso_kg"]: m["repeticiones"] for m in marcas["repeticiones_por_peso"]}
    reps_hoy: dict[float, int] = {}
    for fila in filas_fuerza:
        peso = _peso(fila)
        if peso > 0:
            reps_hoy[peso] = max(reps_hoy.get(peso, 0), fila.repeticiones)
    for peso, reps in sorted(reps_hoy.items(), reverse=True):
        if peso in reps_previas and reps > reps_previas[peso]:
            prs.append(
                {"tipo": "REPETICIONES", "peso_kg": peso, "valor": reps, "anterior": reps_previas[peso]}
            )
    mayor_duracion_previa = marcas["mayor_duracion"]["duracion_segundos"] if marcas["mayor_duracion"] else None
    mayor_duracion_sesion = max((f.duracion_segundos or 0 for f in sesion), default=0)
    if mayor_duracion_sesion > 0 and (
        mayor_duracion_previa is None or mayor_duracion_sesion > mayor_duracion_previa
    ):
        prs.append({
            "tipo": "DURACION",
            "valor": mayor_duracion_sesion,
            "anterior": mayor_duracion_previa or 0,
        })
    return prs


# ---------- Frecuencia (RF-25) ----------
def entrenamientos_por_semana(fechas: list[date], desde: date, hasta: date) -> list[dict]:
    """Cantidad de entrenamientos por semana (de lunes a domingo), incluidas las semanas en cero."""

    def lunes(fecha: date) -> date:
        return fecha - timedelta(days=fecha.weekday())

    conteo = Counter(lunes(fecha) for fecha in fechas)
    semana = lunes(desde)
    ultima = lunes(hasta)
    resultado = []
    while semana <= ultima:
        resultado.append({"semana_inicio": semana, "cantidad": conteo.get(semana, 0)})
        semana += timedelta(days=7)
    return resultado


# ---------- Racha (RF-26) ----------
def calcular_racha(fechas: list[date], meta: int, hoy: date) -> dict:
    """Racha de constancia por semanas (de lunes a domingo).

    - La racha cuenta días entrenados (dos sesiones el mismo día valen uno).
    - Una semana cumple si los días entrenados alcanzan la meta; si no, es un "fallo".
    - Un fallo no rompe la racha: los días de esa semana igual suman.
    - Dos fallos seguidos la rompen: vuelve a 0 y empieza una nueva la semana siguiente.
    - La semana en curso nunca rompe la racha; suma lo entrenado hasta hoy.
    """
    dias = sorted(set(fechas))
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    dias_esta_semana = sum(1 for dia in dias if dia >= lunes_actual)
    anteriores = [dia for dia in dias if dia < lunes_actual]

    racha = 0
    maxima = 0
    fallos_seguidos = 0
    if anteriores:
        semanas = entrenamientos_por_semana(
            anteriores, anteriores[0], lunes_actual - timedelta(days=1)
        )
        for semana in semanas:
            cantidad = semana["cantidad"]
            if cantidad >= meta:
                fallos_seguidos = 0
                racha += cantidad
            else:
                fallos_seguidos += 1
                if fallos_seguidos >= 2:
                    racha = 0
                    fallos_seguidos = 0
                else:
                    racha += cantidad
            maxima = max(maxima, racha)

    actual = racha + dias_esta_semana
    return {
        "racha_actual": actual,
        "racha_maxima": max(maxima, actual),
        "meta_semanal": meta,
        "dias_esta_semana": dias_esta_semana,
        "faltan_esta_semana": max(meta - dias_esta_semana, 0),
        "cumplida_esta_semana": dias_esta_semana >= meta,
        # La semana pasada fue un fallo y esta todavía no alcanza la meta
        "en_riesgo": fallos_seguidos == 1 and dias_esta_semana < meta,
    }