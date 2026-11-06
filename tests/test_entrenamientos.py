from datetime import timedelta

import pytest

from app.models.entrenamiento import Entrenamiento


def serie(peso, repeticiones, completada=True):
    return {"peso_kg": peso, "repeticiones": repeticiones, "completada": completada}


def iniciar_libre(client, headers):
    return client.post("/entrenamientos", json={}, headers=headers)


def crear_rutina(client, headers, ids):
    cuerpo = {
        "nombre": "Fuerza",
        "dias": [
            {
                "dia_semana": "LUNES",
                "nombre": "Pecho",
                "ejercicios": [
                    {"ejercicio_id": ids[0], "series": 4, "repeticiones": 10, "peso_sugerido_kg": 60},
                    {"ejercicio_id": ids[1], "series": 3, "repeticiones": 12},
                ],
            }
        ],
    }
    return client.post("/rutinas", json=cuerpo, headers=headers).json()


def iniciar_desde(client, headers, rutina):
    cuerpo = {"rutina_id": rutina["id"], "dia_id": rutina["dias"][0]["id"]}
    return client.post("/entrenamientos", json=cuerpo, headers=headers)


def test_iniciar_desde_una_rutina_copia_ejercicios_y_series_por_defecto(
    client, ejercicios, headers_usuario
):
    rutina = crear_rutina(client, headers_usuario, ejercicios)

    response = iniciar_desde(client, headers_usuario, rutina)

    assert response.status_code == 201
    cuerpo = response.json()
    assert cuerpo["estado"] == "EN_CURSO"
    assert cuerpo["rutina_id"] == rutina["id"]
    assert cuerpo["titulo"] == "Fuerza · Pecho"
    assert cuerpo["finalizado_en"] is None
    assert [e["ejercicio"]["nombre"] for e in cuerpo["ejercicios"]] == ["Press de banca", "Aperturas"]

    press = cuerpo["ejercicios"][0]
    assert [s["numero"] for s in press["series"]] == [1, 2, 3, 4]
    assert all(s["peso_kg"] == 60 and s["repeticiones"] == 10 for s in press["series"])
    assert not any(s["completada"] for s in press["series"])
    assert len(cuerpo["ejercicios"][1]["series"]) == 3


def test_iniciar_en_estilo_libre_no_requiere_rutina(client, headers_usuario):
    response = iniciar_libre(client, headers_usuario)

    assert response.status_code == 201
    assert response.json()["rutina_id"] is None
    assert response.json()["titulo"] == "Estilo libre"
    assert response.json()["ejercicios"] == []


def test_no_se_puede_iniciar_un_segundo_entrenamiento_en_curso(client, headers_usuario):
    iniciar_libre(client, headers_usuario)

    response = iniciar_libre(client, headers_usuario)

    assert response.status_code == 409


def test_se_consulta_el_entrenamiento_en_curso(client, headers_usuario):
    assert client.get("/entrenamientos/en-curso", headers=headers_usuario).json() is None

    creado = iniciar_libre(client, headers_usuario).json()

    en_curso = client.get("/entrenamientos/en-curso", headers=headers_usuario).json()
    assert en_curso["id"] == creado["id"]


def test_registrar_ejercicios_y_series_en_estilo_libre(client, ejercicios, headers_usuario):
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"

    primera = client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": ejercicios[0], "notas": "Buen agarre", "series": [serie(60, 10), serie(60, 9)]}]},
        headers=headers_usuario,
    )
    assert primera.status_code == 200
    press = primera.json()["ejercicios"][0]
    assert press["notas"] == "Buen agarre"
    assert [s["numero"] for s in press["series"]] == [1, 2]

    # Segunda pasada: se conserva el ejercicio por id, se modifica una serie,
    # se agrega otra y se suma un ejercicio nuevo
    cuerpo = {
        "ejercicios": [
            {
                "id": press["id"],
                "ejercicio_id": ejercicios[0],
                "series": [
                    {"id": press["series"][0]["id"], **serie(62.5, 10)},
                    {"id": press["series"][1]["id"], **serie(60, 9)},
                    serie(57.5, 8, completada=False),
                ],
            },
            {"ejercicio_id": ejercicios[2], "series": [serie(None, 8)]},
        ]
    }
    segunda = client.put(url, json=cuerpo, headers=headers_usuario).json()

    assert [e["ejercicio"]["id"] for e in segunda["ejercicios"]] == [ejercicios[0], ejercicios[2]]
    assert segunda["ejercicios"][0]["id"] == press["id"]
    assert len(segunda["ejercicios"][0]["series"]) == 3
    assert segunda["ejercicios"][0]["series"][0]["peso_kg"] == 62.5
    assert segunda["ejercicios"][1]["series"][0]["peso_kg"] is None


def test_finalizar_calcula_duracion_y_volumen_y_descarta_lo_no_realizado(
    client, db, ejercicios, headers_usuario
):
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"
    client.put(
        url,
        json={
            "ejercicios": [
                {"ejercicio_id": ejercicios[0], "series": [serie(60, 10), serie(62.5, 8), serie(62.5, 8, completada=False)]},
                {"ejercicio_id": ejercicios[1], "series": [serie(20, 12, completada=False)]},
            ]
        },
        headers=headers_usuario,
    )

    # Se simula que el entrenamiento empezó hace 30 minutos
    registro = db.get(Entrenamiento, entrenamiento["id"])
    registro.iniciado_en = registro.iniciado_en - timedelta(minutes=30)
    db.commit()

    response = client.post(
        f"{url}/finalizar",
        json={"agua_ml": 750, "dificultad": 4, "cansancio": 2, "animo": 5},
        headers=headers_usuario,
    )

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["estado"] == "FINALIZADO"
    assert 1800 <= cuerpo["duracion_segundos"] < 1830
    assert cuerpo["finalizado_en"] is not None
    assert cuerpo["series_completadas"] == 2
    assert cuerpo["volumen_total_kg"] == 1100.0
    assert (cuerpo["agua_ml"], cuerpo["dificultad"], cuerpo["cansancio"], cuerpo["animo"]) == (750, 4, 2, 5)
    # Se descartó la serie sin completar y el ejercicio que quedó sin series
    assert len(cuerpo["ejercicios"]) == 1
    assert len(cuerpo["ejercicios"][0]["series"]) == 2


def test_finalizar_sin_series_completadas_devuelve_422(client, ejercicios, headers_usuario):
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"
    client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": ejercicios[0], "series": [serie(60, 10, completada=False)]}]},
        headers=headers_usuario,
    )

    response = client.post(f"{url}/finalizar", json={}, headers=headers_usuario)

    assert response.status_code == 422
    assert client.get(url, headers=headers_usuario).json()["estado"] == "EN_CURSO"


def test_un_entrenamiento_finalizado_no_se_edita_y_permite_iniciar_otro(
    client, ejercicios, headers_usuario
):
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"
    client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": ejercicios[0], "series": [serie(60, 10)]}]},
        headers=headers_usuario,
    )
    client.post(f"{url}/finalizar", json={}, headers=headers_usuario)

    editar = client.put(url, json={"ejercicios": []}, headers=headers_usuario)
    repetir = client.post(f"{url}/finalizar", json={}, headers=headers_usuario)
    nuevo = iniciar_libre(client, headers_usuario)

    assert editar.status_code == 409
    assert repetir.status_code == 409
    assert nuevo.status_code == 201


def test_eliminar_la_rutina_no_borra_el_historial(client, ejercicios, headers_usuario):
    rutina = crear_rutina(client, headers_usuario, ejercicios)
    entrenamiento = iniciar_desde(client, headers_usuario, rutina).json()
    url = f"/entrenamientos/{entrenamiento['id']}"
    ejercicio = entrenamiento["ejercicios"][0]
    client.put(
        url,
        json={
            "ejercicios": [
                {
                    "id": ejercicio["id"],
                    "ejercicio_id": ejercicio["ejercicio"]["id"],
                    "series": [{"id": ejercicio["series"][0]["id"], **serie(60, 10)}],
                }
            ]
        },
        headers=headers_usuario,
    )
    client.post(f"{url}/finalizar", json={}, headers=headers_usuario)

    borrar = client.delete(f"/rutinas/{rutina['id']}", headers=headers_usuario)

    assert borrar.status_code == 204
    historial = client.get(url, headers=headers_usuario)
    assert historial.status_code == 200
    assert historial.json()["rutina_id"] is None
    assert historial.json()["titulo"] == "Fuerza · Pecho"
    assert historial.json()["series_completadas"] == 1


def test_un_usuario_no_accede_al_entrenamiento_de_otro(
    client, headers_usuario, headers_otro_usuario
):
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"

    assert client.get(url, headers=headers_otro_usuario).status_code == 404
    assert client.put(url, json={"ejercicios": []}, headers=headers_otro_usuario).status_code == 404
    assert client.post(f"{url}/finalizar", json={}, headers=headers_otro_usuario).status_code == 404
    assert client.delete(url, headers=headers_otro_usuario).status_code == 404
    assert client.get(url, headers=headers_usuario).status_code == 200


def test_descartar_un_entrenamiento_en_curso_permite_iniciar_otro(client, ejercicios, headers_usuario):
    entrenamiento = iniciar_libre(client, headers_usuario).json()

    descartar = client.delete(f"/entrenamientos/{entrenamiento['id']}", headers=headers_usuario)
    nuevo = iniciar_libre(client, headers_usuario)

    assert descartar.status_code == 204
    assert nuevo.status_code == 201

    url = f"/entrenamientos/{nuevo.json()['id']}"
    client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": ejercicios[0], "series": [serie(60, 10)]}]},
        headers=headers_usuario,
    )
    client.post(f"{url}/finalizar", json={}, headers=headers_usuario)
    assert client.delete(url, headers=headers_usuario).status_code == 409


@pytest.mark.parametrize("serie_invalida", [serie(60, 0), serie(-1, 10), serie(60, 10_000)])
def test_series_invalidas_devuelven_422(client, ejercicios, headers_usuario, serie_invalida):
    entrenamiento = iniciar_libre(client, headers_usuario).json()

    response = client.put(
        f"/entrenamientos/{entrenamiento['id']}",
        json={"ejercicios": [{"ejercicio_id": ejercicios[0], "series": [serie_invalida]}]},
        headers=headers_usuario,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "cambio", [{"dificultad": 6}, {"cansancio": 0}, {"animo": 9}, {"agua_ml": -5}]
)
def test_datos_de_cierre_invalidos_devuelven_422(client, ejercicios, headers_usuario, cambio):
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"
    client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": ejercicios[0], "series": [serie(60, 10)]}]},
        headers=headers_usuario,
    )

    response = client.post(f"{url}/finalizar", json=cambio, headers=headers_usuario)

    assert response.status_code == 422


def test_no_se_puede_entrenar_con_el_ejercicio_personal_de_otro_usuario(
    client, headers_usuario, headers_otro_usuario
):
    ajeno = client.post(
        "/ejercicios",
        json={"nombre": "Ejercicio ajeno", "grupo_principal": "PECHO"},
        headers=headers_usuario,
    ).json()
    entrenamiento = iniciar_libre(client, headers_otro_usuario).json()

    response = client.put(
        f"/entrenamientos/{entrenamiento['id']}",
        json={"ejercicios": [{"ejercicio_id": ajeno["id"], "series": [serie(10, 10)]}]},
        headers=headers_otro_usuario,
    )

    assert response.status_code == 422


def test_un_ejercicio_con_historial_no_se_puede_eliminar(client, headers_usuario):
    propio = client.post(
        "/ejercicios",
        json={"nombre": "Mío", "grupo_principal": "PECHO"},
        headers=headers_usuario,
    ).json()
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"
    client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": propio["id"], "series": [serie(10, 10)]}]},
        headers=headers_usuario,
    )
    client.post(f"{url}/finalizar", json={}, headers=headers_usuario)

    response = client.delete(f"/ejercicios/{propio['id']}", headers=headers_usuario)

    assert response.status_code == 409


def test_cardio_se_registra_por_duracion_y_no_suma_volumen(client, headers_usuario):
    cardio = client.post(
        "/ejercicios",
        json={"nombre": "Cinta de prueba", "grupo_principal": "CARDIO", "tipo_medicion": "TIEMPO"},
        headers=headers_usuario,
    ).json()
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"

    invalido = client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": cardio["id"], "series": [
            {"duracion_segundos": 300, "completada": True},
            {"duracion_segundos": 300, "completada": True},
        ]}]},
        headers=headers_usuario,
    )
    assert invalido.status_code == 422

    guardado = client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": cardio["id"], "series": [
            {"duracion_segundos": 600, "completada": True},
        ]}]},
        headers=headers_usuario,
    )
    assert guardado.status_code == 200
    registro = guardado.json()["ejercicios"][0]["series"][0]
    assert registro["repeticiones"] is None
    assert registro["peso_kg"] is None
    assert registro["duracion_segundos"] == 600

    finalizado = client.post(f"{url}/finalizar", json={}, headers=headers_usuario).json()
    assert finalizado["volumen_total_kg"] == 0

    evolucion = client.get(f"/estadisticas/ejercicios/{cardio['id']}", headers=headers_usuario)
    assert evolucion.status_code == 200
    assert evolucion.json()["tipo_medicion"] == "TIEMPO"
    assert evolucion.json()["duracion_total_segundos"] == 600
    assert evolucion.json()["volumen_total_kg"] == 0
    assert evolucion.json()["marcas"]["mayor_duracion"]["duracion_segundos"] == 600


def test_el_cardio_de_una_rutina_inicia_con_un_registro_de_duracion(client, headers_usuario):
    cardio = client.post(
        "/ejercicios",
        json={"nombre": "Bicicleta de prueba", "grupo_principal": "CARDIO", "tipo_medicion": "TIEMPO"},
        headers=headers_usuario,
    ).json()
    rutina = client.post(
        "/rutinas",
        json={"nombre": "Cardio", "dias": [{
            "dia_semana": "LUNES",
            "nombre": "Resistencia",
            "ejercicios": [{"ejercicio_id": cardio["id"], "duracion_sugerida_segundos": 900}],
        }]},
        headers=headers_usuario,
    ).json()

    entrenamiento = client.post(
        "/entrenamientos",
        json={"rutina_id": rutina["id"], "dia_id": rutina["dias"][0]["id"]},
        headers=headers_usuario,
    )

    assert entrenamiento.status_code == 201
    series = entrenamiento.json()["ejercicios"][0]["series"]
    assert len(series) == 1
    assert series[0]["duracion_segundos"] == 900
    assert series[0]["repeticiones"] is None


def test_el_peso_corporal_se_copia_a_la_serie_y_no_cambia_con_el_perfil(
    client, headers_usuario
):
    perfil = {
        "fecha_nacimiento": "1998-05-20",
        "genero": "MASCULINO",
        "altura_cm": 178,
        "peso_actual_kg": 82.5,
        "objetivo": "GANAR_MASA_MUSCULAR",
        "dias_entrenamiento_semana": 4,
        "unidad_hidratacion": "ML",
    }
    assert client.post("/perfil", json=perfil, headers=headers_usuario).status_code == 201
    ejercicio = client.post(
        "/ejercicios",
        json={"nombre": "Dominada asistida-test", "grupo_principal": "ESPALDA", "usa_peso_corporal": True},
        headers=headers_usuario,
    ).json()
    entrenamiento = iniciar_libre(client, headers_usuario).json()
    url = f"/entrenamientos/{entrenamiento['id']}"

    primera = client.put(
        url,
        json={"ejercicios": [{"ejercicio_id": ejercicio["id"], "series": [
            {"peso_kg": None, "repeticiones": 5, "completada": True},
        ]}]},
        headers=headers_usuario,
    ).json()
    serie_guardada = primera["ejercicios"][0]["series"][0]
    assert serie_guardada["peso_kg"] == 82.5

    assert client.patch("/perfil", json={"peso_actual_kg": 90}, headers=headers_usuario).status_code == 200
    segunda = client.put(
        url,
        json={"ejercicios": [{
            "id": primera["ejercicios"][0]["id"],
            "ejercicio_id": ejercicio["id"],
            "series": [{
                "id": serie_guardada["id"],
                "peso_kg": None,
                "repeticiones": 5,
                "completada": True,
            }],
        }]},
        headers=headers_usuario,
    ).json()
    assert segunda["ejercicios"][0]["series"][0]["peso_kg"] == 82.5

    finalizado = client.post(f"{url}/finalizar", json={}, headers=headers_usuario).json()
    assert finalizado["volumen_total_kg"] == 412.5