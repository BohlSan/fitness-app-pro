from app.services.fechas import hoy

PASSWORD = "secreta123"
PERFIL = {
    "fecha_nacimiento": "1998-05-20",
    "genero": "MASCULINO",
    "altura_cm": 178,
    "peso_actual_kg": 82.5,
    "objetivo": "GANAR_MASA_MUSCULAR",
    "dias_entrenamiento_semana": 4,
    "unidad_hidratacion": "ML",
}


def volver_a_entrar(client, email):
    """Simula cerrar la sesión y volver a iniciarla: se obtiene un token nuevo."""
    respuesta = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert respuesta.status_code == 200
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


def test_toda_la_informacion_se_conserva_despues_de_cerrar_sesion(
    client, ejercicios, entrenar, headers_trainer, headers_usuario
):
    """RF-31: usuarios, ejercicios, rutinas, asignaciones, entrenamientos, series,
    registros de peso e hidratación siguen disponibles al volver a iniciar sesión."""
    # --- Se cargan datos de todos los tipos ---
    client.post("/perfil", json=PERFIL, headers=headers_usuario)
    client.post("/peso", json={"peso_kg": 80, "fecha": "2025-03-01"}, headers=headers_usuario)
    client.post("/hidratacion", json={"cantidad_ml": 500}, headers=headers_usuario)
    propio = client.post(
        "/ejercicios", json={"nombre": "Mi ejercicio", "grupo_principal": "PECHO"}, headers=headers_usuario
    ).json()
    client.post(
        "/rutinas",
        json={
            "nombre": "Mi rutina",
            "dias": [
                {
                    "dia_semana": "LUNES",
                    "nombre": "Pecho",
                    "ejercicios": [{"ejercicio_id": propio["id"], "series": 3, "repeticiones": 10}],
                }
            ],
        },
        headers=headers_usuario,
    )
    entrenamiento_id = entrenar(headers_usuario, ejercicios[0], hoy(), agua_ml=300)

    # El trainer vincula al usuario, cobra una cuota y le asigna una rutina
    codigo = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    vinculo_id = client.post("/vinculo", json={"codigo": codigo}, headers=headers_usuario).json()["vinculo_id"]
    client.post(f"/trainer/vinculos/{vinculo_id}/aceptar", headers=headers_trainer)
    cliente_id = client.get("/auth/me", headers=headers_usuario).json()["id"]
    client.post(f"/trainer/clientes/{cliente_id}/pagos", json={"monto": 25000}, headers=headers_trainer)
    plantilla = client.post(
        "/rutinas",
        json={
            "nombre": "Plan del trainer",
            "dias": [
                {
                    "dia_semana": "MIERCOLES",
                    "nombre": "Espalda",
                    "ejercicios": [{"ejercicio_id": ejercicios[2], "series": 4, "repeticiones": 8}],
                }
            ],
        },
        headers=headers_trainer,
    ).json()
    client.post(
        f"/trainer/clientes/{cliente_id}/asignaciones",
        json={"rutina_id": plantilla["id"]},
        headers=headers_trainer,
    )

    # --- Se "cierra la sesión" y se vuelve a entrar con un token nuevo ---
    usuario = volver_a_entrar(client, "usuario@example.com")
    trainer = volver_a_entrar(client, "trainer@example.com")

    # --- Todo sigue ahí: la persona ---
    assert client.get("/perfil", headers=usuario).json()["altura_cm"] == 178
    pesos = client.get("/peso", params={"hasta": "2025-12-31"}, headers=usuario).json()["registros"]
    assert [(p["fecha"], p["peso_kg"]) for p in pesos] == [("2025-03-01", 80.0)]

    dia = client.get("/hidratacion", headers=usuario).json()
    assert (dia["bebido_ml"], dia["entrenamiento_ml"], dia["total_ml"]) == (500, 300, 800)

    nombres_rutinas = {r["nombre"] for r in client.get("/rutinas", headers=usuario).json()}
    assert nombres_rutinas == {"Mi rutina", "Plan del trainer"}
    assert propio["id"] in [
        e["id"] for e in client.get("/ejercicios", params={"solo_propios": "true"}, headers=usuario).json()
    ]

    historial = client.get("/entrenamientos", headers=usuario).json()
    assert [e["id"] for e in historial] == [entrenamiento_id]
    assert historial[0]["agua_ml"] == 300
    assert historial[0]["ejercicios"][0]["series"][0]["repeticiones"] == 10  # las series persisten

    mi_vinculo = client.get("/vinculo", headers=usuario).json()
    assert mi_vinculo["estado"] == "ACTIVA"
    assert len(mi_vinculo["pagos"]) == 1

    # --- y lo del trainer ---
    clientes = client.get("/trainer/clientes", params={"estado": "ACTIVA"}, headers=trainer).json()
    assert [c["cliente"]["id"] for c in clientes] == [cliente_id]
    base = f"/trainer/clientes/{cliente_id}"
    assert len(client.get(f"{base}/pagos", headers=trainer).json()) == 1
    asignaciones = client.get(f"{base}/asignaciones", headers=trainer).json()
    assert [(a["rutina_nombre"], a["estado"]) for a in asignaciones] == [("Plan del trainer", "ACTIVA")]
    assert len(client.get(f"{base}/entrenamientos", headers=trainer).json()) == 1