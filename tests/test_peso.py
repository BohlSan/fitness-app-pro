import pytest

PERFIL = {
    "fecha_nacimiento": "1998-05-20",
    "genero": "MASCULINO",
    "altura_cm": 178,
    "peso_actual_kg": 82.5,
    "objetivo": "PERDER_PESO",
    "dias_entrenamiento_semana": 4,
    "unidad_hidratacion": "ML",
}

# Las fechas de prueba son de 2025 para no mezclarse con el registro de hoy
# que se crea junto con el perfil
HASTA_2025 = {"hasta": "2025-12-31"}


@pytest.fixture()
def usuario_con_perfil(client, headers_usuario):
    client.post("/perfil", json=PERFIL, headers=headers_usuario)
    return headers_usuario


def registrar(client, headers, peso, fecha=None):
    cuerpo = {"peso_kg": peso}
    if fecha:
        cuerpo["fecha"] = fecha
    return client.post("/peso", json=cuerpo, headers=headers)


def test_los_pesos_de_dias_distintos_se_conservan(client, usuario_con_perfil):
    registrar(client, usuario_con_perfil, 80, "2025-03-01")
    registrar(client, usuario_con_perfil, 79, "2025-03-08")

    response = client.get("/peso", params=HASTA_2025, headers=usuario_con_perfil)

    assert response.status_code == 200
    assert [(r["fecha"], r["peso_kg"]) for r in response.json()["registros"]] == [
        ("2025-03-01", 80.0),
        ("2025-03-08", 79.0),
    ]


def test_cargar_el_peso_del_mismo_dia_lo_corrige_sin_duplicar(client, usuario_con_perfil):
    registrar(client, usuario_con_perfil, 80, "2025-03-01")
    registrar(client, usuario_con_perfil, 79.5, "2025-03-01")

    registros = client.get("/peso", params=HASTA_2025, headers=usuario_con_perfil).json()["registros"]

    assert [(r["fecha"], r["peso_kg"]) for r in registros] == [("2025-03-01", 79.5)]


def test_el_peso_actual_del_perfil_sigue_al_registro_mas_reciente(client, usuario_con_perfil):
    registrar(client, usuario_con_perfil, 90, "2025-03-01")  # más viejo que el de hoy
    assert client.get("/perfil", headers=usuario_con_perfil).json()["peso_actual_kg"] == 82.5

    registrar(client, usuario_con_perfil, 81)  # hoy

    assert client.get("/perfil", headers=usuario_con_perfil).json()["peso_actual_kg"] == 81.0


def test_la_evolucion_incluye_variacion_y_tendencia(client, usuario_con_perfil):
    for fecha, peso in [("2025-03-01", 80), ("2025-03-08", 79), ("2025-03-15", 78)]:
        registrar(client, usuario_con_perfil, peso, fecha)

    evolucion = client.get("/peso", params=HASTA_2025, headers=usuario_con_perfil).json()

    assert evolucion["peso_inicial"] == 80.0
    assert evolucion["peso_actual"] == 78.0
    assert evolucion["variacion_kg"] == -2.0
    assert evolucion["tendencia"]["direccion"] == "BAJA"
    assert evolucion["tendencia"]["pendiente_kg_semana"] == -1.0
    assert len(evolucion["tendencia"]["puntos"]) == 3


def test_no_se_puede_registrar_un_peso_con_fecha_futura(client, usuario_con_perfil):
    response = registrar(client, usuario_con_perfil, 80, "2999-01-01")

    assert response.status_code == 422


@pytest.mark.parametrize("peso", [0, -5, 20, 401])
def test_pesos_invalidos_devuelven_422(client, usuario_con_perfil, peso):
    assert registrar(client, usuario_con_perfil, peso).status_code == 422


def test_sin_perfil_completo_no_se_puede_registrar_el_peso(client, headers_usuario):
    response = registrar(client, headers_usuario, 80)

    assert response.status_code == 409


def test_el_trainer_no_accede_al_peso_corporal(client, headers_trainer):
    assert client.get("/peso", headers=headers_trainer).status_code == 403