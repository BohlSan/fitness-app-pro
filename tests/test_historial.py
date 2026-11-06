from datetime import date

from app.models.entrenamiento import Entrenamiento


def entrenamiento_finalizado(client, db, headers, ejercicio_id, fecha, dificultad=None):
    """Hace un entrenamiento completo y le fija la fecha indicada."""
    creado = client.post("/entrenamientos", json={}, headers=headers).json()
    url = f"/entrenamientos/{creado['id']}"
    client.put(
        url,
        json={
            "ejercicios": [
                {
                    "ejercicio_id": ejercicio_id,
                    "series": [{"peso_kg": 60, "repeticiones": 10, "completada": True}],
                }
            ]
        },
        headers=headers,
    )
    client.post(f"{url}/finalizar", json={"dificultad": dificultad}, headers=headers)

    registro = db.get(Entrenamiento, creado["id"])
    registro.fecha = fecha
    db.commit()
    return creado["id"]


def test_el_historial_solo_muestra_los_entrenamientos_finalizados_propios(
    client, db, ejercicios, headers_usuario, headers_otro_usuario
):
    entrenamiento_finalizado(client, db, headers_usuario, ejercicios[0], date(2026, 10, 5))
    entrenamiento_finalizado(client, db, headers_usuario, ejercicios[0], date(2026, 10, 20))
    entrenamiento_finalizado(client, db, headers_otro_usuario, ejercicios[0], date(2026, 10, 7))
    client.post("/entrenamientos", json={}, headers=headers_usuario)  # queda en curso

    response = client.get("/entrenamientos", headers=headers_usuario)

    assert response.status_code == 200
    # Más reciente primero; sin el entrenamiento en curso ni el de la otra persona
    assert [e["fecha"] for e in response.json()] == ["2026-10-20", "2026-10-05"]


def test_el_historial_incluye_los_datos_de_cada_sesion(client, db, ejercicios, headers_usuario):
    entrenamiento_finalizado(
        client, db, headers_usuario, ejercicios[0], date(2026, 10, 5), dificultad=3
    )

    sesion = client.get("/entrenamientos", headers=headers_usuario).json()[0]

    assert sesion["titulo"] == "Estilo libre"
    assert sesion["fecha"] == "2026-10-05"
    assert sesion["dificultad"] == 3
    assert sesion["duracion_segundos"] is not None
    assert [e["ejercicio"]["nombre"] for e in sesion["ejercicios"]] == ["Press de banca"]
    assert sesion["volumen_total_kg"] == 600.0


def test_filtrar_por_dia(client, db, ejercicios, headers_usuario):
    for fecha in [date(2026, 10, 5), date(2026, 10, 20)]:
        entrenamiento_finalizado(client, db, headers_usuario, ejercicios[0], fecha)

    response = client.get(
        "/entrenamientos",
        params={"desde": "2026-10-20", "hasta": "2026-10-20"},
        headers=headers_usuario,
    )

    assert [e["fecha"] for e in response.json()] == ["2026-10-20"]


def test_filtrar_por_periodo_semana_y_mes(client, db, ejercicios, headers_usuario):
    for fecha in [date(2026, 9, 30), date(2026, 10, 5), date(2026, 10, 12), date(2026, 10, 20)]:
        entrenamiento_finalizado(client, db, headers_usuario, ejercicios[0], fecha)

    def fechas(**params):
        respuesta = client.get("/entrenamientos", params=params, headers=headers_usuario)
        return [e["fecha"] for e in respuesta.json()]

    # Mes de octubre
    assert fechas(desde="2026-10-01", hasta="2026-10-31") == ["2026-10-20", "2026-10-12", "2026-10-05"]
    # Semana del lunes 12 al domingo 18
    assert fechas(desde="2026-10-12", hasta="2026-10-18") == ["2026-10-12"]
    # Períodos abiertos
    assert fechas(desde="2026-10-12") == ["2026-10-20", "2026-10-12"]
    assert fechas(hasta="2026-10-05") == ["2026-10-05", "2026-09-30"]


def test_un_periodo_invertido_devuelve_422(client, headers_usuario):
    response = client.get(
        "/entrenamientos",
        params={"desde": "2026-10-20", "hasta": "2026-10-01"},
        headers=headers_usuario,
    )

    assert response.status_code == 422


def test_calendario_muestra_todas_las_rutinas_previstas_en_un_dia(
    client, headers_usuario, headers_otro_usuario
):
    for nombre in ("Fuerza A", "Cardio B"):
        creada = client.post(
            "/rutinas",
            json={"nombre": nombre, "dias": [{
                "dia_semana": "LUNES", "nombre": f"Día {nombre}", "ejercicios": []
            }]},
            headers=headers_usuario,
        )
        assert creada.status_code == 201

    ajena = client.post(
        "/rutinas",
        json={"nombre": "Rutina ajena", "dias": [{
            "dia_semana": "LUNES", "nombre": "Lunes", "ejercicios": []
        }]},
        headers=headers_otro_usuario,
    )
    assert ajena.status_code == 201

    response = client.get(
        "/entrenamientos/calendario/planificados",
        params={"anio": 2026, "mes": 10},
        headers=headers_usuario,
    )

    assert response.status_code == 200
    assert [dia["fecha"] for dia in response.json()] == [
        "2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26"
    ]
    for dia in response.json():
        assert {rutina["rutina_nombre"] for rutina in dia["rutinas"]} == {"Fuerza A", "Cardio B"}
        assert len(dia["rutinas"]) == 2


def test_el_historial_se_pagina(client, db, ejercicios, headers_usuario):
    for fecha in [date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3)]:
        entrenamiento_finalizado(client, db, headers_usuario, ejercicios[0], fecha)

    primera = client.get("/entrenamientos", params={"limite": 2, "offset": 0}, headers=headers_usuario)
    segunda = client.get("/entrenamientos", params={"limite": 2, "offset": 2}, headers=headers_usuario)

    assert [e["fecha"] for e in primera.json()] == ["2026-10-03", "2026-10-02"]
    assert [e["fecha"] for e in segunda.json()] == ["2026-10-01"]


def test_el_calendario_agrupa_por_dia_con_la_dificultad_maxima(
    client, db, ejercicios, headers_usuario, headers_otro_usuario
):
    e = ejercicios[0]
    entrenamiento_finalizado(client, db, headers_usuario, e, date(2026, 10, 5), dificultad=2)
    entrenamiento_finalizado(client, db, headers_usuario, e, date(2026, 10, 5), dificultad=4)
    entrenamiento_finalizado(client, db, headers_usuario, e, date(2026, 10, 12))
    entrenamiento_finalizado(client, db, headers_usuario, e, date(2026, 9, 30), dificultad=5)  # otro mes
    entrenamiento_finalizado(client, db, headers_otro_usuario, e, date(2026, 10, 5), dificultad=3)  # otra persona

    response = client.get(
        "/entrenamientos/calendario",
        params={"anio": 2026, "mes": 10},
        headers=headers_usuario,
    )

    assert response.status_code == 200
    assert response.json() == [
        {"fecha": "2026-10-05", "cantidad": 2, "dificultad_max": 4},
        {"fecha": "2026-10-12", "cantidad": 1, "dificultad_max": None},
    ]


def test_el_calendario_valida_el_mes(client, headers_usuario):
    response = client.get(
        "/entrenamientos/calendario",
        params={"anio": 2026, "mes": 13},
        headers=headers_usuario,
    )

    assert response.status_code == 422