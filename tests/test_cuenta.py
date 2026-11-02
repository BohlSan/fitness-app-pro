import pytest
from sqlalchemy import func, select

from app.models.ejercicio import Ejercicio
from app.models.entrenamiento import Entrenamiento
from app.models.hidratacion import RegistroHidratacion
from app.models.perfil import PerfilUsuario, RegistroPeso
from app.models.rutina import Rutina
from app.models.trainer import PagoCliente
from app.models.usuario import Usuario
from app.services.fechas import hoy

PASSWORD = "secreta123"
PERFIL = {
    "fecha_nacimiento": "1998-05-20",
    "genero": "FEMENINO",
    "altura_cm": 165,
    "peso_actual_kg": 60,
    "objetivo": "MANTENER_PESO",
    "dias_entrenamiento_semana": 3,
    "unidad_hidratacion": "ML",
}
CONFIRMACION = {"confirmacion": "ELIMINAR"}


def iniciar_sesion(client, email, password=PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def contar(db, modelo, *condiciones):
    return db.scalar(select(func.count()).select_from(modelo).where(*condiciones))


def cuerpo_rutina(ids, nombre="Plan"):
    return {
        "nombre": nombre,
        "dias": [
            {
                "dia_semana": "LUNES",
                "nombre": "Pecho",
                "ejercicios": [
                    {"ejercicio_id": ids[0], "series": 4, "repeticiones": 10},
                    {"ejercicio_id": ids[1], "series": 3, "repeticiones": 12},
                ],
            }
        ],
    }


def vincular_y_activar(client, headers_trainer, headers_cliente):
    codigo = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    vinculo_id = client.post("/vinculo", json={"codigo": codigo}, headers=headers_cliente).json()["vinculo_id"]
    client.post(f"/trainer/vinculos/{vinculo_id}/aceptar", headers=headers_trainer)
    return client.get("/auth/me", headers=headers_cliente).json()["id"]


# ---------- Datos de la cuenta ----------
def test_se_puede_cambiar_el_nombre(client, headers_usuario):
    response = client.patch("/cuenta/datos", json={"nombre": "  Nuevo Nombre "}, headers=headers_usuario)

    assert response.status_code == 200
    assert response.json()["nombre"] == "Nuevo Nombre"
    assert client.get("/auth/me", headers=headers_usuario).json()["nombre"] == "Nuevo Nombre"


def test_cambiar_el_email_exige_la_contrasena_actual(client, headers_usuario):
    sin_clave = client.patch("/cuenta/datos", json={"email": "nuevo@example.com"}, headers=headers_usuario)
    clave_mala = client.patch(
        "/cuenta/datos",
        json={"email": "nuevo@example.com", "password_actual": "incorrecta1"},
        headers=headers_usuario,
    )
    correcto = client.patch(
        "/cuenta/datos",
        json={"email": "NUEVO@example.com", "password_actual": PASSWORD},
        headers=headers_usuario,
    )

    assert (sin_clave.status_code, clave_mala.status_code, correcto.status_code) == (403, 403, 200)
    assert correcto.json()["email"] == "nuevo@example.com"
    assert iniciar_sesion(client, "nuevo@example.com").status_code == 200
    assert iniciar_sesion(client, "usuario@example.com").status_code == 401


def test_no_se_puede_usar_el_email_de_otra_cuenta(client, headers_usuario, headers_otro_usuario):
    response = client.patch(
        "/cuenta/datos",
        json={"email": "otro@example.com", "password_actual": PASSWORD},
        headers=headers_usuario,
    )

    assert response.status_code == 409


def test_se_puede_cambiar_la_contrasena(client, headers_usuario):
    incorrecta = client.put(
        "/cuenta/password",
        json={"password_actual": "incorrecta1", "password_nueva": "nueva-clave-1"},
        headers=headers_usuario,
    )
    debil = client.put(
        "/cuenta/password",
        json={"password_actual": PASSWORD, "password_nueva": "corta"},
        headers=headers_usuario,
    )
    correcta = client.put(
        "/cuenta/password",
        json={"password_actual": PASSWORD, "password_nueva": "nueva-clave-1"},
        headers=headers_usuario,
    )

    assert (incorrecta.status_code, debil.status_code, correcta.status_code) == (403, 422, 204)
    assert iniciar_sesion(client, "usuario@example.com", PASSWORD).status_code == 401
    assert iniciar_sesion(client, "usuario@example.com", "nueva-clave-1").status_code == 200


def test_los_endpoints_de_cuenta_exigen_sesion(client):
    assert client.patch("/cuenta/datos", json={"nombre": "X"}).status_code == 401
    assert client.post("/cuenta/eliminar", json=CONFIRMACION).status_code == 401


# ---------- Eliminar la cuenta ----------
@pytest.mark.parametrize("texto", ["eliminar", "ELIMINAR ", "", "SI"])
def test_eliminar_la_cuenta_exige_la_confirmacion_exacta(client, headers_usuario, texto):
    response = client.post("/cuenta/eliminar", json={"confirmacion": texto}, headers=headers_usuario)

    assert response.status_code == 422
    assert client.get("/auth/me", headers=headers_usuario).status_code == 200


def test_eliminar_la_cuenta_borra_sus_datos_y_deja_intactos_los_de_otras_personas(
    client, db, ejercicios, entrenar, headers_usuario, headers_otro_usuario
):
    for headers in (headers_usuario, headers_otro_usuario):
        client.post("/perfil", json=PERFIL, headers=headers)
        client.post("/rutinas", json=cuerpo_rutina(ejercicios), headers=headers)
        entrenar(headers, ejercicios[0], hoy())
    client.post("/hidratacion", json={"cantidad_ml": 500}, headers=headers_usuario)

    response = client.post("/cuenta/eliminar", json=CONFIRMACION, headers=headers_usuario)

    assert response.status_code == 204
    assert iniciar_sesion(client, "usuario@example.com").status_code == 401
    assert client.get("/auth/me", headers=headers_usuario).status_code == 401  # el token ya no sirve

    assert contar(db, Usuario, Usuario.email == "usuario@example.com") == 0
    assert contar(db, RegistroHidratacion) == 0
    # Queda únicamente lo de la otra persona
    assert contar(db, PerfilUsuario) == 1
    assert contar(db, RegistroPeso) == 1
    assert contar(db, Rutina) == 1
    assert contar(db, Entrenamiento) == 1
    assert client.get("/perfil", headers=headers_otro_usuario).status_code == 200
    assert len(client.get("/rutinas", headers=headers_otro_usuario).json()) == 1
    assert len(client.get("/entrenamientos", headers=headers_otro_usuario).json()) == 1


def test_al_eliminar_a_un_cliente_se_cierra_su_relacion_con_el_trainer(
    client, db, headers_trainer, headers_usuario
):
    cliente_id = vincular_y_activar(client, headers_trainer, headers_usuario)
    client.post(f"/trainer/clientes/{cliente_id}/pagos", json={"monto": 25000}, headers=headers_trainer)
    assert contar(db, PagoCliente) == 1

    client.post("/cuenta/eliminar", json=CONFIRMACION, headers=headers_usuario)

    activos = client.get("/trainer/clientes", params={"estado": "ACTIVA"}, headers=headers_trainer).json()
    assert activos == []
    assert contar(db, PagoCliente) == 0


def test_al_eliminar_a_un_trainer_sus_clientes_conservan_rutinas_e_historial(
    client, db, ejercicios, entrenar, headers_trainer, headers_usuario
):
    sin_uso = client.post(
        "/ejercicios", json={"nombre": "Solo mío", "grupo_principal": "PECHO"}, headers=headers_trainer
    ).json()
    compartido = client.post(
        "/ejercicios", json={"nombre": "Compartido", "grupo_principal": "ESPALDA"}, headers=headers_trainer
    ).json()
    cliente_id = vincular_y_activar(client, headers_trainer, headers_usuario)
    plantilla = client.post(
        "/rutinas", json=cuerpo_rutina([compartido["id"], ejercicios[0]]), headers=headers_trainer
    ).json()
    client.post(
        f"/trainer/clientes/{cliente_id}/asignaciones",
        json={"rutina_id": plantilla["id"]},
        headers=headers_trainer,
    )
    entrenar(headers_usuario, ejercicios[0], hoy())

    response = client.post("/cuenta/eliminar", json=CONFIRMACION, headers=headers_trainer)

    assert response.status_code == 204
    # El cliente conserva su rutina asignada (sin autor) y todo su historial
    rutinas = client.get("/rutinas", headers=headers_usuario).json()
    assert len(rutinas) == 1
    assert rutinas[0]["autor_id"] is None
    assert rutinas[0]["propietario_id"] == cliente_id
    assert len(client.get("/entrenamientos", headers=headers_usuario).json()) == 1
    assert client.get("/vinculo", headers=headers_usuario).json() is None

    # El ejercicio sin uso se borra; el que usa la rutina del cliente queda sin autor
    assert contar(db, Ejercicio, Ejercicio.id == sin_uso["id"]) == 0
    assert contar(db, Ejercicio, Ejercicio.id == compartido["id"]) == 1
    assert db.scalar(select(Ejercicio.creador_id).where(Ejercicio.id == compartido["id"])) is None