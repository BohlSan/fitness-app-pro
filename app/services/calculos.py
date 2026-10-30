from collections import Counter, namedtuple
from datetime import date, timedelta

# Una serie realizada. Cualquier objeto con estos atributos sirve (por ejemplo, una fila de SQL)
FilaSerie = namedtuple("FilaSerie", "entrenamiento_id fecha peso_kg repeticiones")

# Por debajo de este cambio semanal, el peso se considera estable
UMBRAL_TENDENCIA_ESTABLE_KG_SEMANA = 0.1


def volumen_serie(peso_kg: float | None, repeticiones: int) -> float:
    return float(peso_kg or 0) * repeticiones


def volumen_series(series) -> float:
    """Volumen = Σ (peso × repeticiones) de las series completadas (RF-23).

    Funciona con cualquier objeto que tenga peso_kg, repeticiones y completada.
    Las series sin peso (peso corporal) aportan 0.
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
            },
        )
        sesion["volumen_kg"] += _peso(fila) * fila.repeticiones
        sesion["peso_max_kg"] = max(sesion["peso_max_kg"], _peso(fila))
        sesion["series"] += 1
        sesion["repeticiones"] += fila.repeticiones

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
        "mejor_volumen_sesion": mejor_volumen,
        "repeticiones_por_peso": sorted(por_peso.values(), key=lambda m: -m["peso_kg"]),
    }


def detectar_prs(previas, sesion) -> list[dict]:
    """Récords que una sesión rompió respecto de las sesiones anteriores del ejercicio."""
    if not previas or not sesion:
        return []

    marcas = mejores_marcas(previas)
    prs = []

    peso_max = max(_peso(f) for f in sesion)
    if marcas["mayor_peso"] and peso_max > marcas["mayor_peso"]["peso_kg"]:
        prs.append({"tipo": "PESO", "valor": peso_max, "anterior": marcas["mayor_peso"]["peso_kg"]})

    volumen = round(sum(_peso(f) * f.repeticiones for f in sesion), 2)
    if marcas["mejor_volumen_sesion"] and volumen > marcas["mejor_volumen_sesion"]["volumen_kg"]:
        prs.append(
            {"tipo": "VOLUMEN", "valor": volumen, "anterior": marcas["mejor_volumen_sesion"]["volumen_kg"]}
        )

    reps_previas = {m["peso_kg"]: m["repeticiones"] for m in marcas["repeticiones_por_peso"]}
    reps_hoy: dict[float, int] = {}
    for fila in sesion:
        peso = _peso(fila)
        if peso > 0:
            reps_hoy[peso] = max(reps_hoy.get(peso, 0), fila.repeticiones)
    for peso, reps in sorted(reps_hoy.items(), reverse=True):
        if peso in reps_previas and reps > reps_previas[peso]:
            prs.append(
                {"tipo": "REPETICIONES", "peso_kg": peso, "valor": reps, "anterior": reps_previas[peso]}
            )
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