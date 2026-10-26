import pytest
from sqlalchemy import select

from app.models.auditoria import RegistroAuditoria
from app.models.ejercicio import Ejercicio, GrupoMuscular
from app.models.rutina import DiaRutina, RutinaEjercicio
from app.schemas.ejercicio import EjercicioCreate
from app.services.ejercicio_factory import EjercicioFactory


@pytest.fixture()
def ejercicios(db):
    """Tres ejercicios del catálogo. Devuelve sus ids."""
    ids = []
    for nombre, grupo in [
        ("Press de banca", GrupoMuscular.PECHO),
        ("Aperturas", GrupoMuscular.PECHO),
        ("Dominadas", GrupoMuscular.ESPALDA),
    ]:
        ejercicio = EjercicioFactory.crear_base(
            EjercicioCreate(nombre=nombre, grupo_principal=grupo)
        )
        db.add(ejercicio)
        db.commit()
        ids.append(ejercicio.id)
    return ids


def rutina_valida(ids, nombre="Fuerza"):
    return {
        "nombre": nombre,
        "descripcion": "Rutina de prueba",
        "dias": [
            {
                "dia_semana": "LUNES",
                "nombre": "Pecho",
                "ejercicios": [
                    {
                        "ejercicio_id": ids[0],
                        "series": 4,
                        "repeticiones": 10,
                        "peso_sugerido_kg": 60,
                        "descanso_segundos": 90,
                    },
                    {"ejercicio_id": ids[1], "series": 3, "repeticiones": 12},
                ],
            },
            {
                "dia_semana": "MIERCOLES",
                "nombre": "Espalda",
                "ejercicios": [{"ejercicio_id": ids[2], "series": 4, "repeticiones": 8}],
            },
        ],
    }


def test_crear_rutina_con_dias_y_ejercicios(client, ejercicios, headers_usuario):
    cuerpo = rutina_valida(ejercicios)
    cuerpo["dias"].reverse()  # se envían desordenados a propósito

    response = client.post("/rutinas", json=cuerpo, headers=headers_usuario)

    assert response.status_code == 201
    rutina = response.json()
    usuario_id = client.get("/auth/me", headers=headers_usuario).json()["id"]
    assert rutina["autor_id"] == usuario_id
    assert rutina["propietario_id"] == usuario_id
    assert [dia["dia_semana"] for dia in rutina["dias"]] == ["LUNES", "MIERCOLES"]

    lunes = rutina["dias"][0]
    assert [e["ejercicio"]["nombre"] for e in lunes["ejercicios"]] == ["Press de banca", "Aperturas"]
    assert [e["orden"] for e in lunes["ejercicios"]] == [0, 1]
    assert lunes["ejercicios"][0]["series"] == 4
    assert lunes["ejercicios"][0]["peso_sugerido_kg"] == 60


def test_un_trainer_puede_crear_su_propia_rutina(client, ejercicios, headers_trainer):
    response = client.post("/rutinas", json=rutina_valida(ejercicios), headers=headers_trainer)

    assert response.status_code == 201


def test_listar_rutinas_solo_muestra_las_propias(
    client, ejercicios, headers_usuario, headers_otro_usuario
):
    client.post("/rutinas", json=rutina_valida(ejercicios), headers=headers_usuario)

    propias = client.get("/rutinas", headers=headers_usuario)
    ajenas = client.get("/rutinas", headers=headers_otro_usuario)

    assert len(propias.json()) == 1
    assert ajenas.json() == []


def test_un_usuario_no_accede_a_la_rutina_de_otro(
    client, ejercicios, headers_usuario, headers_otro_usuario
):
    creada = client.post("/rutinas", json=rutina_valida(ejercicios), headers=headers_usuario).json()
    url = f"/rutinas/{creada['id']}"

    ver = client.get(url, headers=headers_otro_usuario)
    editar = client.put(url, json=rutina_valida(ejercicios, "Robada"), headers=headers_otro_usuario)
    borrar = client.delete(url, headers=headers_otro_usuario)

    assert ver.status_code == 404
    assert editar.status_code == 404
    assert borrar.status_code == 404
    assert client.get(url, headers=headers_usuario).json()["nombre"] == "Fuerza"


def test_editar_rutina_modifica_agrega_y_quita_conservando_los_ids(
    client, ejercicios, headers_usuario
):
    e1, e2, e3 = ejercicios
    creada = client.post("/rutinas", json=rutina_valida(ejercicios), headers=headers_usuario).json()
    lunes = creada["dias"][0]
    primero = lunes["ejercicios"][0]

    cuerpo = {
        "nombre": "Renombrada",
        "descripcion": None,
        "dias": [
            {
                "id": lunes["id"],
                "dia_semana": "LUNES",
                "nombre": "Pecho y tríceps",
                "ejercicios": [
                    # se conserva y se modifica
                    {"id": primero["id"], "ejercicio_id": e1, "series": 5, "repeticiones": 5, "peso_sugerido_kg": 80},
                    # se agrega (e2 se quita al no venir en la lista)
                    {"ejercicio_id": e3, "series": 3, "repeticiones": 15},
                ],
            }
            # el miércoles se quita al no venir en la lista
        ],
    }

    response = client.put(f"/rutinas/{creada['id']}", json=cuerpo, headers=headers_usuario)

    assert response.status_code == 200
    rutina = response.json()
    assert rutina["nombre"] == "Renombrada"
    assert rutina["descripcion"] is None
    assert len(rutina["dias"]) == 1
    assert rutina["dias"][0]["id"] == lunes["id"]
    assert rutina["dias"][0]["nombre"] == "Pecho y tríceps"

    items = rutina["dias"][0]["ejercicios"]
    assert [item["ejercicio"]["id"] for item in items] == [e1, e3]
    assert [item["orden"] for item in items] == [0, 1]
    assert items[0]["id"] == primero["id"]
    assert items[0]["series"] == 5
    assert items[0]["peso_sugerido_kg"] == 80


def test_eliminar_rutina_borra_sus_dias_pero_no_los_ejercicios(
    client, db, ejercicios, headers_usuario
):
    creada = client.post("/rutinas", json=rutina_valida(ejercicios), headers=headers_usuario).json()

    borrar = client.delete(f"/rutinas/{creada['id']}", headers=headers_usuario)

    assert borrar.status_code == 204
    assert client.get(f"/rutinas/{creada['id']}", headers=headers_usuario).status_code == 404
    assert db.scalars(select(DiaRutina)).all() == []
    assert db.scalars(select(RutinaEjercicio)).all() == []
    assert len(db.scalars(select(Ejercicio)).all()) == 3


def test_el_mismo_ejercicio_puede_estar_en_varias_rutinas_sin_duplicarse(
    client, db, ejercicios, headers_usuario
):
    primera = client.post("/rutinas", json=rutina_valida(ejercicios, "Rutina A"), headers=headers_usuario)
    segunda = client.post("/rutinas", json=rutina_valida(ejercicios, "Rutina B"), headers=headers_usuario)

    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert len(db.scalars(select(Ejercicio)).all()) == 3


def test_no_se_aceptan_dos_dias_iguales(client, ejercicios, headers_usuario):
    cuerpo = rutina_valida(ejercicios)
    cuerpo["dias"][1]["dia_semana"] = "LUNES"

    response = client.post("/rutinas", json=cuerpo, headers=headers_usuario)

    assert response.status_code == 422


def test_una_rutina_sin_dias_devuelve_422(client, headers_usuario):
    response = client.post("/rutinas", json={"nombre": "Vacía", "dias": []}, headers=headers_usuario)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "cambio",
    [
        {"series": 0},
        {"series": 21},
        {"repeticiones": 0},
        {"repeticiones": -1},
        {"peso_sugerido_kg": -5},
        {"descanso_segundos": -1},
    ],
)
def test_valores_numericos_invalidos_devuelven_422(client, ejercicios, headers_usuario, cambio):
    cuerpo = rutina_valida(ejercicios)
    cuerpo["dias"][0]["ejercicios"][0].update(cambio)

    response = client.post("/rutinas", json=cuerpo, headers=headers_usuario)

    assert response.status_code == 422


def test_un_ejercicio_inexistente_devuelve_422_y_no_guarda_nada(client, ejercicios, headers_usuario):
    cuerpo = rutina_valida([ejercicios[0], 999999, ejercicios[2]])

    response = client.post("/rutinas", json=cuerpo, headers=headers_usuario)

    assert response.status_code == 422
    assert client.get("/rutinas", headers=headers_usuario).json() == []


def test_no_se_puede_usar_el_ejercicio_personal_de_otro_usuario(
    client, ejercicios, headers_usuario, headers_otro_usuario
):
    ajeno = client.post(
        "/ejercicios",
        json={"nombre": "Ejercicio ajeno", "grupo_principal": "PECHO"},
        headers=headers_usuario,
    ).json()

    response = client.post(
        "/rutinas",
        json=rutina_valida([ajeno["id"], ejercicios[1], ejercicios[2]]),
        headers=headers_otro_usuario,
    )

    assert response.status_code == 422


def test_un_ejercicio_en_uso_no_se_puede_eliminar(client, ejercicios, headers_usuario):
    propio = client.post(
        "/ejercicios",
        json={"nombre": "Mío", "grupo_principal": "PECHO"},
        headers=headers_usuario,
    ).json()
    rutina = client.post(
        "/rutinas",
        json=rutina_valida([propio["id"], ejercicios[0], ejercicios[1]]),
        headers=headers_usuario,
    ).json()

    bloqueado = client.delete(f"/ejercicios/{propio['id']}", headers=headers_usuario)
    assert bloqueado.status_code == 409

    client.delete(f"/rutinas/{rutina['id']}", headers=headers_usuario)
    liberado = client.delete(f"/ejercicios/{propio['id']}", headers=headers_usuario)
    assert liberado.status_code == 204


def test_las_operaciones_sobre_rutinas_quedan_auditadas(client, db, ejercicios, headers_usuario):
    creada = client.post("/rutinas", json=rutina_valida(ejercicios), headers=headers_usuario).json()
    url = f"/rutinas/{creada['id']}"
    client.put(url, json=rutina_valida(ejercicios, "Modificada"), headers=headers_usuario)
    client.delete(url, headers=headers_usuario)

    acciones = db.scalars(select(RegistroAuditoria.accion).order_by(RegistroAuditoria.id)).all()

    assert list(acciones) == ["CREAR_RUTINA", "MODIFICAR_RUTINA", "ELIMINAR_RUTINA"]