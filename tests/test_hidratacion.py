import pytest

from app.services.fechas import hoy

PERFIL = {
    "fecha_nacimiento": "1998-05-20",
    "genero": "FEMENINO",
    "altura_cm": 165,
    "peso_actual_kg": 60,
    "objetivo": "MANTENER_PESO",
    "dias_entrenamiento_semana": 3,
    "unidad_hidratacion": "ML",
}


@pytest.fixture()
def usuario(client, headers_usuario):
    client.post("/perfil", json=PERFIL, headers=headers_usuario)
    return headers_usuario


def tomar(client, headers, ml, **extra):
    return client.post("/hidratacion", json={"cantidad_ml": ml, **extra}, headers=headers)


def test_las_tomas_del_dia_se_suman_contra_la_meta_por_defecto(client, usuario):
    tomar(client, usuario, 250)
    response = tomar(client, usuario, 250)

    assert response.status_code == 201
    dia = response.json()
    assert dia["fecha"] == hoy().isoformat()
    assert dia["bebido_ml"] == 500
    assert dia["total_ml"] == 500
    assert dia["meta_ml"] == 2000
    assert dia["porcentaje"] == 25
    assert dia["cumplida"] is False
    assert len(dia["registros"]) == 2
    assert dia["ml_vaso"] == 250


def test_el_agua_del_entrenamiento_suma_al_total_del_dia(client, ejercicios, entrenar, usuario):
    entrenar(usuario, ejercicios[0], hoy(), agua_ml=500)
    tomar(client, usuario, 250)

    dia = client.get("/hidratacion", headers=usuario).json()

    assert dia["bebido_ml"] == 250
    assert dia["entrenamiento_ml"] == 500
    assert dia["total_ml"] == 750


def test_se_puede_deshacer_una_toma(client, usuario):
    tomar(client, usuario, 250)
    segunda = tomar(client, usuario, 500).json()
    ultimo = segunda["registros"][-1]

    response = client.delete(f"/hidratacion/{ultimo['id']}", headers=usuario)

    assert response.status_code == 200
    assert response.json()["total_ml"] == 250


def test_no_se_puede_deshacer_la_toma_de_otra_persona(
    client, usuario, headers_otro_usuario
):
    client.post("/perfil", json=PERFIL, headers=headers_otro_usuario)
    ajena = tomar(client, headers_otro_usuario, 300).json()["registros"][0]

    response = client.delete(f"/hidratacion/{ajena['id']}", headers=usuario)

    assert response.status_code == 404
    assert client.get("/hidratacion", headers=headers_otro_usuario).json()["total_ml"] == 300


def test_la_meta_y_las_equivalencias_son_configurables(client, usuario):
    cambio = client.patch(
        "/perfil",
        json={"unidad_hidratacion": "VASOS", "ml_vaso": 300, "meta_hidratacion_ml": 3000},
        headers=usuario,
    )
    assert cambio.status_code == 200

    dia = client.get("/hidratacion", headers=usuario).json()

    assert dia["unidad"] == "VASOS"
    assert dia["ml_vaso"] == 300
    assert dia["meta_ml"] == 3000


def test_el_historial_rellena_los_dias_sin_registros(client, usuario):
    tomar(client, usuario, 1000)

    response = client.get("/hidratacion/historial", params={"dias": 3}, headers=usuario)

    assert response.status_code == 200
    dias = response.json()
    assert len(dias) == 3
    assert [d["total_ml"] for d in dias] == [0, 0, 1000]
    assert dias[-1]["fecha"] == hoy().isoformat()
    assert dias[-1]["cumplio"] is False


@pytest.mark.parametrize("cantidad", [0, 5, 3001, -10])
def test_cantidades_invalidas_devuelven_422(client, usuario, cantidad):
    assert tomar(client, usuario, cantidad).status_code == 422


def test_no_se_registra_agua_con_fecha_futura(client, usuario):
    assert tomar(client, usuario, 250, fecha="2999-01-01").status_code == 422


def test_sin_perfil_completo_no_se_registra_hidratacion(client, headers_usuario):
    assert tomar(client, headers_usuario, 250).status_code == 409
    assert client.get("/hidratacion", headers=headers_usuario).status_code == 409


def test_el_trainer_no_accede_a_la_hidratacion(client, headers_trainer):
    assert client.get("/hidratacion", headers=headers_trainer).status_code == 403