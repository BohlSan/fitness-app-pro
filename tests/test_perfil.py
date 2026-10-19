from datetime import date

import pytest
from sqlalchemy import select

from app.models.perfil import RegistroPeso
from app.services import perfil_service
from app.services.fechas import calcular_edad

PERFIL_VALIDO = {
    "fecha_nacimiento": "1998-05-20",
    "genero": "MASCULINO",
    "altura_cm": 178,
    "peso_actual_kg": 82.5,
    "objetivo": "GANAR_MASA_MUSCULAR",
    "dias_entrenamiento_semana": 4,
    "unidad_hidratacion": "ML",
}


def test_obtener_perfil_sin_completar_devuelve_404(client, headers_usuario):
    response = client.get("/perfil", headers=headers_usuario)

    assert response.status_code == 404


def test_crear_perfil_devuelve_edad_y_registra_el_primer_peso(
    client, db, headers_usuario
):
    response = client.post("/perfil", json=PERFIL_VALIDO, headers=headers_usuario)

    assert response.status_code == 201
    cuerpo = response.json()
    assert cuerpo["edad"] == calcular_edad(date(1998, 5, 20))
    assert cuerpo["peso_actual_kg"] == 82.5

    registros = db.scalars(select(RegistroPeso)).all()
    assert len(registros) == 1
    assert registros[0].peso_kg == 82.5


def test_crear_perfil_dos_veces_devuelve_409(client, headers_usuario):
    client.post("/perfil", json=PERFIL_VALIDO, headers=headers_usuario)

    response = client.post("/perfil", json=PERFIL_VALIDO, headers=headers_usuario)

    assert response.status_code == 409


@pytest.mark.parametrize(
    "cambio",
    [
        {"altura_cm": 30},
        {"peso_actual_kg": -5},
        {"dias_entrenamiento_semana": 8},
        {"fecha_nacimiento": "2999-01-01"},
        {"objetivo": "VOLAR"},
    ],
)
def test_perfil_con_datos_invalidos_devuelve_422(client, headers_usuario, cambio):
    response = client.post(
        "/perfil", json={**PERFIL_VALIDO, **cambio}, headers=headers_usuario
    )

    assert response.status_code == 422


def test_hidratacion_en_botellas_exige_los_ml_de_la_botella(client, headers_usuario):
    datos = {**PERFIL_VALIDO, "unidad_hidratacion": "BOTELLAS"}

    response = client.post("/perfil", json=datos, headers=headers_usuario)

    assert response.status_code == 422


def test_cambiar_hidratacion_a_mililitros_borra_los_ml_de_la_botella(
    client, headers_usuario
):
    datos = {**PERFIL_VALIDO, "unidad_hidratacion": "BOTELLAS", "ml_botella": 750}
    creado = client.post("/perfil", json=datos, headers=headers_usuario)
    assert creado.json()["ml_botella"] == 750

    response = client.patch(
        "/perfil", json={"unidad_hidratacion": "ML"}, headers=headers_usuario
    )

    assert response.status_code == 200
    assert response.json()["ml_botella"] is None


def test_actualizar_perfil_modifica_solo_los_campos_enviados(client, headers_usuario):
    client.post("/perfil", json=PERFIL_VALIDO, headers=headers_usuario)

    response = client.patch(
        "/perfil", json={"dias_entrenamiento_semana": 5}, headers=headers_usuario
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["dias_entrenamiento_semana"] == 5
    assert cuerpo["altura_cm"] == 178
    assert cuerpo["objetivo"] == "GANAR_MASA_MUSCULAR"


def test_actualizar_peso_el_mismo_dia_no_duplica_el_registro(
    client, db, headers_usuario
):
    client.post("/perfil", json=PERFIL_VALIDO, headers=headers_usuario)

    response = client.patch(
        "/perfil", json={"peso_actual_kg": 81.0}, headers=headers_usuario
    )

    assert response.status_code == 200
    assert response.json()["peso_actual_kg"] == 81.0
    registros = db.scalars(select(RegistroPeso)).all()
    assert len(registros) == 1
    assert registros[0].peso_kg == 81.0


def test_guardar_peso_en_dias_distintos_crea_registros_separados(
    client, db, headers_usuario
):
    usuario_id = client.get("/auth/me", headers=headers_usuario).json()["id"]

    perfil_service.guardar_peso_del_dia(db, usuario_id, 80.0, fecha=date(2026, 1, 1))
    perfil_service.guardar_peso_del_dia(db, usuario_id, 79.5, fecha=date(2026, 1, 8))
    db.commit()

    registros = db.scalars(select(RegistroPeso).order_by(RegistroPeso.fecha)).all()
    assert [registro.peso_kg for registro in registros] == [80.0, 79.5]


def test_trainer_no_puede_acceder_al_perfil_de_usuario(client, headers_trainer):
    response = client.get("/perfil", headers=headers_trainer)

    assert response.status_code == 403