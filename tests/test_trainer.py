import pytest
from sqlalchemy import select

from app.models.trainer import AsignacionRutina, EstadoAsignacion
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


def cuerpo_rutina(ids, nombre="Plan base"):
    return {
        "nombre": nombre,
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


def cuerpo_de(rutina, nombre):
    """Arma el cuerpo de un PUT a partir de una rutina existente."""
    return {
        "nombre": nombre,
        "descripcion": rutina["descripcion"],
        "dias": [
            {
                "id": dia["id"],
                "dia_semana": dia["dia_semana"],
                "nombre": dia["nombre"],
                "ejercicios": [
                    {
                        "id": item["id"],
                        "ejercicio_id": item["ejercicio"]["id"],
                        "series": item["series"],
                        "repeticiones": item["repeticiones"],
                        "peso_sugerido_kg": item["peso_sugerido_kg"],
                        "descanso_segundos": item["descanso_segundos"],
                    }
                    for item in dia["ejercicios"]
                ],
            }
            for dia in rutina["dias"]
        ],
    }


def solicitar(client, headers_trainer, headers_cliente):
    """El cliente pide vincularse con el código del trainer. Devuelve (vinculo_id, cliente_id)."""
    codigo = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    respuesta = client.post("/vinculo", json={"codigo": codigo}, headers=headers_cliente)
    cliente_id = client.get("/auth/me", headers=headers_cliente).json()["id"]
    return respuesta.json()["vinculo_id"], cliente_id


def vinculo_activo(client, headers_trainer, headers_cliente):
    vinculo_id, cliente_id = solicitar(client, headers_trainer, headers_cliente)
    client.post(f"/trainer/vinculos/{vinculo_id}/aceptar", headers=headers_trainer)
    return vinculo_id, cliente_id


# ---------- Código y relación ----------
def test_el_trainer_tiene_un_codigo_estable_y_puede_regenerarlo(client, headers_trainer, headers_usuario):
    primero = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    segundo = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    assert len(primero) == 8
    assert primero == segundo

    nuevo = client.post("/trainer/codigo/regenerar", headers=headers_trainer).json()["codigo_enlace"]
    assert nuevo != primero

    viejo = client.post("/vinculo", json={"codigo": primero}, headers=headers_usuario)
    assert viejo.status_code == 404


def test_un_codigo_inexistente_devuelve_404(client, headers_usuario):
    response = client.post("/vinculo", json={"codigo": "ZZZZZZZZ"}, headers=headers_usuario)

    assert response.status_code == 404


def test_la_solicitud_queda_pendiente_hasta_que_el_trainer_la_acepta(
    client, headers_trainer, headers_usuario
):
    vinculo_id, _ = solicitar(client, headers_trainer, headers_usuario)

    pendientes = client.get("/trainer/clientes", params={"estado": "PENDIENTE"}, headers=headers_trainer).json()
    panel = client.get("/trainer/panel", headers=headers_trainer).json()

    assert [p["vinculo_id"] for p in pendientes] == [vinculo_id]
    assert pendientes[0]["estado"] == "PENDIENTE"
    assert panel["solicitudes_pendientes"] == 1
    assert panel["clientes_activos"] == 0
    assert client.get("/vinculo", headers=headers_usuario).json()["estado"] == "PENDIENTE"


def test_un_usuario_solo_puede_tener_un_entrenador_vigente(
    client, headers_trainer, headers_otro_trainer, headers_usuario
):
    solicitar(client, headers_trainer, headers_usuario)

    otro_codigo = client.get("/trainer/codigo", headers=headers_otro_trainer).json()["codigo_enlace"]
    con_otro = client.post("/vinculo", json={"codigo": otro_codigo}, headers=headers_usuario)
    con_el_mismo = solicitar(client, headers_trainer, headers_usuario)

    assert con_otro.status_code == 409
    assert con_el_mismo is not None  # el segundo intento con el mismo trainer también se rechaza
    assert len(client.get("/trainer/clientes", headers=headers_trainer).json()) == 1


def test_al_aceptar_la_relacion_queda_activa_con_fecha_de_inicio(
    client, headers_trainer, headers_usuario
):
    vinculo_id, _ = solicitar(client, headers_trainer, headers_usuario)

    response = client.post(f"/trainer/vinculos/{vinculo_id}/aceptar", headers=headers_trainer)

    assert response.status_code == 200
    assert response.json()["estado"] == "ACTIVA"
    assert response.json()["inicio"] == hoy().isoformat()
    assert client.get("/vinculo", headers=headers_usuario).json()["estado"] == "ACTIVA"


def test_el_trainer_no_ve_datos_de_un_cliente_hasta_que_la_relacion_esta_activa(
    client, headers_trainer, headers_usuario
):
    _, cliente_id = solicitar(client, headers_trainer, headers_usuario)

    response = client.get(f"/trainer/clientes/{cliente_id}", headers=headers_trainer)

    assert response.status_code == 404


# ---------- Permisos (RF-13 y RF-30) ----------
RUTAS_DEL_CLIENTE = [
    "",
    "/pagos",
    "/asignaciones",
    "/entrenamientos",
    "/estadisticas/resumen",
    "/estadisticas/ejercicios",
    "/peso",
    "/racha",
]


@pytest.mark.parametrize("ruta", RUTAS_DEL_CLIENTE)
def test_un_trainer_no_accede_a_datos_de_usuarios_que_no_son_sus_clientes(
    client, headers_trainer, headers_usuario, ruta
):
    cliente_id = client.get("/auth/me", headers=headers_usuario).json()["id"]

    response = client.get(f"/trainer/clientes/{cliente_id}{ruta}", headers=headers_trainer)

    assert response.status_code == 404


@pytest.mark.parametrize("ruta", RUTAS_DEL_CLIENTE)
def test_un_trainer_no_accede_a_los_clientes_de_otro_trainer(
    client, headers_trainer, headers_otro_trainer, headers_usuario, ruta
):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)

    response = client.get(f"/trainer/clientes/{cliente_id}{ruta}", headers=headers_otro_trainer)

    assert response.status_code == 404


def test_un_usuario_comun_no_accede_a_los_endpoints_del_trainer(client, headers_usuario):
    assert client.get("/trainer/clientes", headers=headers_usuario).status_code == 403
    assert client.get("/trainer/codigo", headers=headers_usuario).status_code == 403
    assert client.get("/trainer/actividad", headers=headers_usuario).status_code == 403


# ---------- Información del cliente (RF-12 y RF-29) ----------
def test_el_trainer_consulta_la_informacion_basica_del_cliente(
    client, headers_trainer, headers_usuario
):
    client.post("/perfil", json=PERFIL, headers=headers_usuario)
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)

    detalle = client.get(f"/trainer/clientes/{cliente_id}", headers=headers_trainer).json()

    assert detalle["email"] == "usuario@example.com"
    assert detalle["altura_cm"] == 165
    assert detalle["peso_actual_kg"] == 60.0
    assert detalle["objetivo"] == "MANTENER_PESO"
    assert detalle["dias_entrenamiento_semana"] == 3
    assert detalle["edad"] is not None
    assert "fecha_nacimiento" not in detalle  # datos que el trainer no necesita


def test_el_trainer_consulta_el_historial_y_el_detalle_de_entrenamientos_del_cliente(
    client, ejercicios, entrenar, headers_trainer, headers_usuario, headers_otro_usuario
):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    propio = entrenar(headers_usuario, ejercicios[0], hoy())
    ajeno = entrenar(headers_otro_usuario, ejercicios[0], hoy())
    base = f"/trainer/clientes/{cliente_id}"

    historial = client.get(f"{base}/entrenamientos", headers=headers_trainer).json()
    detalle = client.get(f"{base}/entrenamientos/{propio}", headers=headers_trainer)
    de_otra_persona = client.get(f"{base}/entrenamientos/{ajeno}", headers=headers_trainer)

    assert [e["id"] for e in historial] == [propio]
    assert detalle.status_code == 200
    assert detalle.json()["ejercicios"][0]["series"][0]["repeticiones"] == 10
    assert de_otra_persona.status_code == 404


def test_el_trainer_consulta_el_progreso_del_cliente(
    client, ejercicios, entrenar, headers_trainer, headers_usuario
):
    client.post("/perfil", json=PERFIL, headers=headers_usuario)
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    entrenar(headers_usuario, ejercicios[0], hoy())
    base = f"/trainer/clientes/{cliente_id}"

    resumen = client.get(f"{base}/estadisticas/resumen", headers=headers_trainer).json()
    entrenados = client.get(f"{base}/estadisticas/ejercicios", headers=headers_trainer).json()
    evolucion = client.get(f"{base}/estadisticas/ejercicios/{ejercicios[0]}", headers=headers_trainer)
    peso = client.get(f"{base}/peso", headers=headers_trainer).json()
    racha = client.get(f"{base}/racha", headers=headers_trainer).json()

    assert resumen["cantidad_entrenamientos"] == 1
    assert [e["nombre"] for e in entrenados] == ["Press de banca"]
    assert evolucion.status_code == 200
    assert len(peso["registros"]) >= 1
    assert racha["racha_actual"] == 1


# ---------- Cuota y pagos (RF-13) ----------
def test_el_trainer_registra_pagos_y_la_cuota_queda_al_dia(client, headers_trainer, headers_usuario):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    base = f"/trainer/clientes/{cliente_id}"
    assert client.get(base, headers=headers_trainer).json()["estado_cuota"] == "PENDIENTE"

    pago = client.post(f"{base}/pagos", json={"monto": 25000, "concepto": "Octubre"}, headers=headers_trainer)
    assert pago.status_code == 201
    assert pago.json()["fecha"] == hoy().isoformat()
    assert client.get(base, headers=headers_trainer).json()["estado_cuota"] == "AL_DIA"

    cambio = client.put(f"{base}/cuota", json={"estado_cuota": "VENCIDA"}, headers=headers_trainer)
    assert cambio.json()["estado_cuota"] == "VENCIDA"

    pagos = client.get(f"{base}/pagos", headers=headers_trainer).json()
    assert [(p["monto"], p["concepto"]) for p in pagos] == [(25000, "Octubre")]

    # El cliente ve el estado de su cuota y sus pagos
    mi_vinculo = client.get("/vinculo", headers=headers_usuario).json()
    assert mi_vinculo["estado_cuota"] == "VENCIDA"
    assert len(mi_vinculo["pagos"]) == 1


@pytest.mark.parametrize(
    "pago", [{"monto": 0}, {"monto": -5}, {"monto": 1000, "fecha": "2999-01-01"}]
)
def test_los_pagos_invalidos_devuelven_422(client, headers_trainer, headers_usuario, pago):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)

    response = client.post(f"/trainer/clientes/{cliente_id}/pagos", json=pago, headers=headers_trainer)

    assert response.status_code == 422


# ---------- Rutinas asignadas (RF-11, RF-09 y RF-30) ----------
def test_asignar_una_rutina_la_copia_para_el_cliente(
    client, ejercicios, headers_trainer, headers_usuario
):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    trainer_id = client.get("/auth/me", headers=headers_trainer).json()["id"]
    plantilla = client.post("/rutinas", json=cuerpo_rutina(ejercicios), headers=headers_trainer).json()

    response = client.post(
        f"/trainer/clientes/{cliente_id}/asignaciones",
        json={"rutina_id": plantilla["id"]},
        headers=headers_trainer,
    )

    assert response.status_code == 201
    asignacion = response.json()
    assert asignacion["estado"] == "ACTIVA"
    assert asignacion["fecha_asignacion"] == hoy().isoformat()
    assert asignacion["rutina_nombre"] == "Plan base"

    del_cliente = client.get("/rutinas", headers=headers_usuario).json()
    assert len(del_cliente) == 1
    copia = del_cliente[0]
    assert copia["id"] != plantilla["id"]
    assert copia["autor_id"] == trainer_id
    assert copia["propietario_id"] == cliente_id
    assert [e["ejercicio"]["id"] for e in copia["dias"][0]["ejercicios"]] == ejercicios[:2]

    # La plantilla sigue siendo del trainer y la copia no aparece en sus rutinas
    assert [r["id"] for r in client.get("/rutinas", headers=headers_trainer).json()] == [plantilla["id"]]
    listadas = client.get(f"/trainer/clientes/{cliente_id}/asignaciones", headers=headers_trainer).json()
    assert [a["rutina_id"] for a in listadas] == [copia["id"]]


def test_el_trainer_modifica_la_rutina_asignada_pero_no_las_de_otras_personas(
    client, ejercicios, headers_trainer, headers_otro_trainer, headers_usuario, headers_otro_usuario
):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    plantilla = client.post("/rutinas", json=cuerpo_rutina(ejercicios), headers=headers_trainer).json()
    client.post(
        f"/trainer/clientes/{cliente_id}/asignaciones",
        json={"rutina_id": plantilla["id"]},
        headers=headers_trainer,
    )
    copia = client.get("/rutinas", headers=headers_usuario).json()[0]

    modificada = client.put(
        f"/rutinas/{copia['id']}", json=cuerpo_de(copia, "Plan de Ana"), headers=headers_trainer
    )
    assert modificada.status_code == 200
    assert client.get(f"/rutinas/{copia['id']}", headers=headers_usuario).json()["nombre"] == "Plan de Ana"
    assert client.get(f"/rutinas/{plantilla['id']}", headers=headers_trainer).json()["nombre"] == "Plan base"

    # Otro trainer no puede tocarla
    ajeno = client.put(
        f"/rutinas/{copia['id']}", json=cuerpo_de(copia, "Robada"), headers=headers_otro_trainer
    )
    assert ajeno.status_code == 404

    # Una rutina de una persona que no es su cliente tampoco
    de_otra_persona = client.post(
        "/rutinas", json=cuerpo_rutina(ejercicios), headers=headers_otro_usuario
    ).json()
    assert client.get(f"/rutinas/{de_otra_persona['id']}", headers=headers_trainer).status_code == 404


def test_solo_se_pueden_asignar_rutinas_propias(
    client, ejercicios, headers_trainer, headers_otro_trainer, headers_usuario
):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    del_cliente = client.post("/rutinas", json=cuerpo_rutina(ejercicios), headers=headers_usuario).json()
    de_otro_trainer = client.post(
        "/rutinas", json=cuerpo_rutina(ejercicios), headers=headers_otro_trainer
    ).json()

    for rutina in (del_cliente, de_otro_trainer):
        response = client.post(
            f"/trainer/clientes/{cliente_id}/asignaciones",
            json={"rutina_id": rutina["id"]},
            headers=headers_trainer,
        )
        assert response.status_code == 404


def test_finalizar_la_relacion_revoca_el_acceso_y_cierra_las_asignaciones(
    client, db, ejercicios, headers_trainer, headers_otro_trainer, headers_usuario
):
    vinculo_id, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)
    plantilla = client.post("/rutinas", json=cuerpo_rutina(ejercicios), headers=headers_trainer).json()
    client.post(
        f"/trainer/clientes/{cliente_id}/asignaciones",
        json={"rutina_id": plantilla["id"]},
        headers=headers_trainer,
    )
    copia = client.get("/rutinas", headers=headers_usuario).json()[0]

    response = client.post(f"/trainer/vinculos/{vinculo_id}/finalizar", headers=headers_trainer)

    assert response.status_code == 200
    assert response.json()["estado"] == "FINALIZADA"
    assert client.get(f"/trainer/clientes/{cliente_id}", headers=headers_trainer).status_code == 404
    assert (
        client.put(
            f"/rutinas/{copia['id']}", json=cuerpo_de(copia, "Ya no"), headers=headers_trainer
        ).status_code
        == 404
    )
    estados = {a.estado for a in db.scalars(select(AsignacionRutina)).all()}
    assert estados == {EstadoAsignacion.FINALIZADA}

    # La persona queda libre para vincularse con otro entrenador
    otro_codigo = client.get("/trainer/codigo", headers=headers_otro_trainer).json()["codigo_enlace"]
    nueva = client.post("/vinculo", json={"codigo": otro_codigo}, headers=headers_usuario)
    assert nueva.status_code == 201


def test_el_cliente_puede_finalizar_su_relacion(client, headers_trainer, headers_usuario):
    _, cliente_id = vinculo_activo(client, headers_trainer, headers_usuario)

    response = client.delete("/vinculo", headers=headers_usuario)

    assert response.status_code == 204
    assert client.get("/vinculo", headers=headers_usuario).json() is None
    assert client.get("/trainer/clientes", params={"estado": "ACTIVA"}, headers=headers_trainer).json() == []
    assert client.get(f"/trainer/clientes/{cliente_id}", headers=headers_trainer).status_code == 404
    assert client.delete("/vinculo", headers=headers_usuario).status_code == 404