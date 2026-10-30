from datetime import date, datetime, time, timezone

from app.models.entrenamiento import Entrenamiento


def entrenar(client, db, headers, ejercicio_id, series, fecha, agua_ml=None, duracion=None):
    """Hace un entrenamiento completo en una fecha dada. series = [(peso, repeticiones)]."""
    creado = client.post("/entrenamientos", json={}, headers=headers).json()
    url = f"/entrenamientos/{creado['id']}"
    client.put(
        url,
        json={
            "ejercicios": [
                {
                    "ejercicio_id": ejercicio_id,
                    "series": [
                        {"peso_kg": peso, "repeticiones": reps, "completada": True}
                        for peso, reps in series
                    ],
                }
            ]
        },
        headers=headers,
    )
    client.post(f"{url}/finalizar", json={"agua_ml": agua_ml}, headers=headers)

    registro = db.get(Entrenamiento, creado["id"])
    registro.fecha = fecha
    registro.iniciado_en = datetime.combine(fecha, time(10, 0), tzinfo=timezone.utc)
    if duracion is not None:
        registro.duracion_segundos = duracion
    db.commit()
    return creado["id"]


def test_el_resumen_calcula_las_estadisticas_del_periodo(client, db, ejercicios, headers_usuario):
    e = ejercicios[0]
    entrenar(client, db, headers_usuario, e, [(60, 10)], date(2026, 10, 5), agua_ml=500, duracion=3600)
    entrenar(client, db, headers_usuario, e, [(60, 10), (60, 10)], date(2026, 10, 7), agua_ml=1000, duracion=1800)
    entrenar(client, db, headers_usuario, e, [(50, 10)], date(2026, 10, 20), duracion=2400)

    response = client.get(
        "/estadisticas/resumen",
        params={"desde": "2026-10-05", "hasta": "2026-10-25"},
        headers=headers_usuario,
    )

    assert response.status_code == 200
    resumen = response.json()
    assert resumen["cantidad_entrenamientos"] == 3
    assert resumen["volumen_total_kg"] == 2300.0
    assert resumen["duracion_promedio_segundos"] == 2600
    assert resumen["agua_promedio_ml"] == 750  # solo cuentan los que registraron agua
    assert resumen["frecuencia_semanal"] == 1.0  # 3 entrenamientos en 3 semanas
    assert [(s["semana_inicio"], s["cantidad"]) for s in resumen["por_semana"]] == [
        ("2026-10-05", 2),
        ("2026-10-12", 0),
        ("2026-10-19", 1),
    ]


def test_el_resumen_sin_entrenamientos_devuelve_ceros(client, headers_usuario):
    resumen = client.get("/estadisticas/resumen", headers=headers_usuario).json()

    assert resumen["cantidad_entrenamientos"] == 0
    assert resumen["volumen_total_kg"] == 0
    assert resumen["frecuencia_semanal"] == 0
    assert resumen["duracion_promedio_segundos"] is None
    assert resumen["por_semana"] == []


def test_el_resumen_no_incluye_los_entrenamientos_de_otras_personas(
    client, db, ejercicios, headers_usuario, headers_otro_usuario
):
    entrenar(client, db, headers_otro_usuario, ejercicios[0], [(100, 10)], date(2026, 10, 5))

    resumen = client.get("/estadisticas/resumen", headers=headers_usuario).json()

    assert resumen["cantidad_entrenamientos"] == 0


def test_un_periodo_invertido_devuelve_422(client, headers_usuario):
    response = client.get(
        "/estadisticas/resumen",
        params={"desde": "2026-10-20", "hasta": "2026-10-01"},
        headers=headers_usuario,
    )

    assert response.status_code == 422


def test_se_listan_los_ejercicios_entrenados_con_sus_marcas(client, db, ejercicios, headers_usuario):
    entrenar(client, db, headers_usuario, ejercicios[0], [(60, 10)], date(2026, 10, 5))
    entrenar(client, db, headers_usuario, ejercicios[0], [(62.5, 6)], date(2026, 10, 12))
    entrenar(client, db, headers_usuario, ejercicios[1], [(20, 12)], date(2026, 10, 7))

    response = client.get("/estadisticas/ejercicios", headers=headers_usuario)

    assert response.status_code == 200
    lista = response.json()
    assert [e["nombre"] for e in lista] == ["Press de banca", "Aperturas"]  # el más reciente primero
    assert lista[0]["sesiones"] == 2
    assert lista[0]["mayor_peso_kg"] == 62.5
    assert lista[0]["mejor_volumen_sesion_kg"] == 600.0


def test_la_evolucion_de_un_ejercicio_respeta_el_periodo_pero_las_marcas_son_historicas(
    client, db, ejercicios, headers_usuario
):
    e = ejercicios[0]
    entrenar(client, db, headers_usuario, e, [(60, 10), (60, 8)], date(2026, 10, 5))  # volumen 1080
    entrenar(client, db, headers_usuario, e, [(62.5, 6)], date(2026, 10, 12))  # volumen 375

    completa = client.get(f"/estadisticas/ejercicios/{e}", headers=headers_usuario).json()
    assert [s["fecha"] for s in completa["sesiones"]] == ["2026-10-05", "2026-10-12"]
    assert completa["volumen_total_kg"] == 1455.0
    assert completa["marcas"]["mayor_peso"]["peso_kg"] == 62.5
    assert [(m["peso_kg"], m["repeticiones"]) for m in completa["marcas"]["repeticiones_por_peso"]] == [
        (62.5, 6),
        (60.0, 10),
    ]

    recorte = client.get(
        f"/estadisticas/ejercicios/{e}", params={"desde": "2026-10-10"}, headers=headers_usuario
    ).json()
    assert [s["fecha"] for s in recorte["sesiones"]] == ["2026-10-12"]
    assert recorte["volumen_total_kg"] == 375.0
    # La mejor sesión sigue siendo la del día 5, aunque quede fuera del período
    assert recorte["marcas"]["mejor_volumen_sesion"]["volumen_kg"] == 1080.0


def test_un_ejercicio_sin_historial_devuelve_404(client, ejercicios, headers_usuario):
    response = client.get(f"/estadisticas/ejercicios/{ejercicios[0]}", headers=headers_usuario)

    assert response.status_code == 404


def test_se_identifican_los_records_de_una_sesion(client, db, ejercicios, headers_usuario):
    primera = entrenar(client, db, headers_usuario, ejercicios[0], [(60, 10)], date(2026, 10, 1))
    segunda = entrenar(client, db, headers_usuario, ejercicios[0], [(65, 5)], date(2026, 10, 8))

    # La primera vez no hay con qué comparar
    assert client.get(f"/estadisticas/entrenamientos/{primera}/prs", headers=headers_usuario).json() == []

    prs = client.get(f"/estadisticas/entrenamientos/{segunda}/prs", headers=headers_usuario).json()
    assert len(prs) == 1
    assert prs[0]["tipo"] == "PESO"
    assert prs[0]["nombre"] == "Press de banca"
    assert (prs[0]["valor"], prs[0]["anterior"]) == (65.0, 60.0)


def test_no_se_consultan_los_records_de_otra_persona(
    client, db, ejercicios, headers_usuario, headers_otro_usuario
):
    ajeno = entrenar(client, db, headers_otro_usuario, ejercicios[0], [(60, 10)], date(2026, 10, 1))

    response = client.get(f"/estadisticas/entrenamientos/{ajeno}/prs", headers=headers_usuario)

    assert response.status_code == 404