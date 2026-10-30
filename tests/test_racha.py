from datetime import date, timedelta

from app.services.calculos import calcular_racha
from app.services.fechas import hoy

META = 3

# Lunes de cada semana: 5, 12, 19 y 26 de octubre de 2026
SEMANA_1 = [date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)]  # 3 días: cumple
SEMANA_2 = [date(2026, 10, 12), date(2026, 10, 13)]  # 2 días: fallo

PERFIL_3_DIAS = {
    "fecha_nacimiento": "1998-05-20",
    "genero": "MASCULINO",
    "altura_cm": 178,
    "peso_actual_kg": 82.5,
    "objetivo": "MANTENER_PESO",
    "dias_entrenamiento_semana": 3,
    "unidad_hidratacion": "ML",
}


def test_ejemplo_del_equipo_dos_semanas_seguidas_sin_cumplir_rompen_la_racha():
    # Semana 3 completa sin entrenar; hoy es miércoles de la semana 4
    racha = calcular_racha(SEMANA_1 + SEMANA_2, META, hoy=date(2026, 10, 28))

    assert racha["racha_actual"] == 0
    assert racha["racha_maxima"] == 5  # llegó a 3 + 2
    assert racha["en_riesgo"] is False


def test_un_solo_fallo_no_rompe_la_racha_y_avisa_el_riesgo():
    # Semana 3 en curso (miércoles 21): la 2 fue un fallo
    racha = calcular_racha(SEMANA_1 + SEMANA_2, META, hoy=date(2026, 10, 21))

    assert racha["racha_actual"] == 5
    assert racha["en_riesgo"] is True
    assert racha["faltan_esta_semana"] == 3


def test_la_semana_en_curso_suma_lo_entrenado_hasta_hoy():
    fechas = SEMANA_1 + SEMANA_2 + [date(2026, 10, 20)]

    racha = calcular_racha(fechas, META, hoy=date(2026, 10, 21))

    assert racha["racha_actual"] == 6
    assert racha["dias_esta_semana"] == 1
    assert racha["faltan_esta_semana"] == 2
    assert racha["cumplida_esta_semana"] is False


def test_cumplir_la_meta_dos_semanas_seguidas_acumula_sin_riesgo():
    semana_2_completa = [date(2026, 10, 12), date(2026, 10, 13), date(2026, 10, 14)]

    racha = calcular_racha(SEMANA_1 + semana_2_completa, META, hoy=date(2026, 10, 21))

    assert racha["racha_actual"] == 6
    assert racha["en_riesgo"] is False


def test_cumplir_la_meta_despues_de_un_fallo_evita_que_se_rompa():
    semana_3_completa = [date(2026, 10, 19), date(2026, 10, 20), date(2026, 10, 21)]

    # Semana 1 cumple, semana 2 sin entrenar (fallo), semana 3 cumple; hoy ya es la semana 4
    racha = calcular_racha(SEMANA_1 + semana_3_completa, META, hoy=date(2026, 10, 28))

    assert racha["racha_actual"] == 6
    assert racha["racha_maxima"] == 6


def test_sin_entrenamientos_la_racha_es_cero():
    racha = calcular_racha([], META, hoy=date(2026, 10, 28))

    assert racha["racha_actual"] == 0
    assert racha["racha_maxima"] == 0
    assert racha["faltan_esta_semana"] == META


def test_dos_sesiones_el_mismo_dia_cuentan_como_un_dia():
    fechas = [date(2026, 10, 5), date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)]

    racha = calcular_racha(fechas, META, hoy=date(2026, 10, 14))

    assert racha["racha_actual"] == 3


def test_la_racha_del_usuario_se_calcula_desde_sus_entrenamientos(
    client, ejercicios, entrenar, headers_usuario
):
    client.post("/perfil", json=PERFIL_3_DIAS, headers=headers_usuario)
    lunes = hoy() - timedelta(days=hoy().weekday())
    e = ejercicios[0]

    # Hace dos semanas: 3 días (cumple). La semana pasada: 2 días (fallo). Hoy: 1 día
    for desplazamiento in (-14, -13, -12, -7, -6):
        entrenar(headers_usuario, e, lunes + timedelta(days=desplazamiento))
    entrenar(headers_usuario, e, hoy())

    response = client.get("/racha", headers=headers_usuario)

    assert response.status_code == 200
    racha = response.json()
    assert racha["racha_actual"] == 6
    assert racha["racha_maxima"] == 6
    assert racha["meta_semanal"] == 3
    assert racha["dias_esta_semana"] == 1
    assert racha["faltan_esta_semana"] == 2
    assert racha["en_riesgo"] is True


def test_sin_perfil_no_hay_racha(client, headers_usuario):
    assert client.get("/racha", headers=headers_usuario).status_code == 409


def test_el_trainer_no_tiene_racha(client, headers_trainer):
    assert client.get("/racha", headers=headers_trainer).status_code == 403