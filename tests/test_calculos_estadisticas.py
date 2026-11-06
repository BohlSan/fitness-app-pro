from datetime import date

from app.services.calculos import (
    FilaSerie,
    calcular_tendencia,
    detectar_prs,
    entrenamientos_por_semana,
    mejores_marcas,
    volumen_por_sesion,
)


def fila(entrenamiento_id, dia, peso, repeticiones):
    return FilaSerie(entrenamiento_id, date(2026, 10, dia), peso, repeticiones)


# Tres sesiones del mismo ejercicio
SESION_A = [fila(1, 1, 60, 10), fila(1, 1, 60, 8)]  # volumen 1080
SESION_B = [fila(2, 8, 62.5, 6), fila(2, 8, 60, 12)]  # volumen 1095
SESION_C = [fila(3, 15, 62.5, 6)]  # volumen 375


def test_la_tendencia_de_un_peso_que_baja():
    puntos = [(date(2025, 3, 1), 80.0), (date(2025, 3, 8), 79.0), (date(2025, 3, 15), 78.0)]

    tendencia = calcular_tendencia(puntos)

    assert tendencia["direccion"] == "BAJA"
    assert tendencia["pendiente_kg_semana"] == -1.0
    assert [p["peso_kg"] for p in tendencia["puntos"]] == [80.0, 79.0, 78.0]


def test_un_peso_casi_constante_es_estable():
    puntos = [(date(2025, 3, 1), 80.0), (date(2025, 3, 8), 80.05), (date(2025, 3, 15), 80.0)]

    assert calcular_tendencia(puntos)["direccion"] == "ESTABLE"


def test_la_tendencia_necesita_dos_dias_distintos():
    assert calcular_tendencia([]) is None
    assert calcular_tendencia([(date(2025, 3, 1), 80.0)]) is None
    assert calcular_tendencia([(date(2025, 3, 1), 80.0), (date(2025, 3, 1), 79.0)]) is None


def test_el_volumen_por_sesion_agrupa_las_series():
    sesiones = volumen_por_sesion(SESION_A + SESION_B)

    assert [s["volumen_kg"] for s in sesiones] == [1080.0, 1095.0]
    assert sesiones[0]["series"] == 2
    assert sesiones[1]["peso_max_kg"] == 62.5


def test_las_mejores_marcas_conservan_la_mas_antigua_ante_empates():
    marcas = mejores_marcas(SESION_A + SESION_B + SESION_C)

    assert marcas["mayor_peso"]["peso_kg"] == 62.5
    assert marcas["mayor_peso"]["repeticiones"] == 6
    assert marcas["mayor_peso"]["fecha"] == date(2026, 10, 8)  # no la del día 15
    assert marcas["mejor_volumen_sesion"]["volumen_kg"] == 1095.0
    assert [(m["peso_kg"], m["repeticiones"]) for m in marcas["repeticiones_por_peso"]] == [
        (62.5, 6),
        (60.0, 12),
    ]


def test_se_detectan_los_tres_tipos_de_record():
    previas = SESION_A + SESION_B
    sesion = [fila(4, 22, 65, 5), fila(4, 22, 60, 13)]

    prs = detectar_prs(previas, sesion)

    assert {pr["tipo"] for pr in prs} == {"PESO", "VOLUMEN", "REPETICIONES"}
    peso = next(pr for pr in prs if pr["tipo"] == "PESO")
    assert (peso["valor"], peso["anterior"]) == (65.0, 62.5)
    reps = next(pr for pr in prs if pr["tipo"] == "REPETICIONES")
    assert (reps["peso_kg"], reps["valor"], reps["anterior"]) == (60.0, 13, 12)


def test_la_primera_vez_que_se_hace_un_ejercicio_no_es_record():
    assert detectar_prs([], SESION_A) == []


def test_los_entrenamientos_por_semana_incluyen_las_semanas_en_cero():
    fechas = [date(2026, 10, 5), date(2026, 10, 7), date(2026, 10, 20)]

    semanas = entrenamientos_por_semana(fechas, date(2026, 10, 5), date(2026, 10, 25))

    assert [(s["semana_inicio"], s["cantidad"]) for s in semanas] == [
        (date(2026, 10, 5), 2),
        (date(2026, 10, 12), 0),
        (date(2026, 10, 19), 1),
    ]


def test_duracion_de_cardio_se_acumula_y_genera_record():
    cardio_a = FilaSerie(10, date(2026, 10, 1), None, None, 600, "TIEMPO")
    cardio_b = FilaSerie(11, date(2026, 10, 8), None, None, 900, "TIEMPO")

    sesiones = volumen_por_sesion([cardio_a, cardio_b])
    marcas = mejores_marcas([cardio_a, cardio_b])
    prs = detectar_prs([cardio_a], [cardio_b])

    assert [sesion["duracion_total_segundos"] for sesion in sesiones] == [600, 900]
    assert all(sesion["volumen_kg"] == 0 for sesion in sesiones)
    assert marcas["mayor_duracion"]["duracion_segundos"] == 900
    assert prs == [{"tipo": "DURACION", "valor": 900, "anterior": 600}]