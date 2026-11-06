from types import SimpleNamespace

from app.models.ejercicio import Ejercicio, GrupoMuscular
from app.schemas.ejercicio import EjercicioCreate
from app.services.ejercicio_factory import EjercicioFactory


def crear_base(db, nombre, principal, secundario=None):
    datos = EjercicioCreate(
        nombre=nombre, grupo_principal=principal, grupo_secundario=secundario
    )
    ejercicio = EjercicioFactory.crear_base(datos)
    db.add(ejercicio)
    db.commit()
    return ejercicio


def nuevo(nombre="Mi ejercicio", principal="PECHO", **extra):
    return {"nombre": nombre, "grupo_principal": principal, **extra}


def nombres(response):
    return [ejercicio["nombre"] for ejercicio in response.json()]


def test_la_factory_crea_ejercicios_base_sin_creador_y_personales_con_creador():
    datos = EjercicioCreate(nombre="Remo", grupo_principal=GrupoMuscular.ESPALDA)

    base = EjercicioFactory.crear_base(datos)
    personal = EjercicioFactory.crear_personal(datos, SimpleNamespace(id=7))

    assert base.creador_id is None
    assert personal.creador_id == 7


def test_listar_ejercicios_sin_token_devuelve_401(client):
    response = client.get("/ejercicios")

    assert response.status_code == 401


def test_listar_grupos_musculares(client, headers_usuario):
    response = client.get("/ejercicios/grupos", headers=headers_usuario)

    assert response.status_code == 200
    assert {"valor": "PECHO", "etiqueta": "Pecho"} in response.json()


def test_filtrar_por_grupo_muscular(client, db, headers_usuario):
    crear_base(db, "Press de banca", GrupoMuscular.PECHO)
    crear_base(db, "Dominadas", GrupoMuscular.ESPALDA)
    crear_base(db, "Aperturas", GrupoMuscular.PECHO)

    response = client.get(
        "/ejercicios", params={"grupo": "PECHO"}, headers=headers_usuario
    )

    assert response.status_code == 200
    assert nombres(response) == ["Aperturas", "Press de banca"]


def test_buscar_por_nombre_ignora_mayusculas(client, db, headers_usuario):
    crear_base(db, "Press de banca", GrupoMuscular.PECHO)
    crear_base(db, "Dominadas", GrupoMuscular.ESPALDA)

    response = client.get("/ejercicios", params={"q": "PRESS"}, headers=headers_usuario)

    assert nombres(response) == ["Press de banca"]


def test_solo_propios_excluye_el_catalogo(client, db, headers_usuario):
    crear_base(db, "Press de banca", GrupoMuscular.PECHO)
    client.post("/ejercicios", json=nuevo("Mi press"), headers=headers_usuario)

    response = client.get(
        "/ejercicios", params={"solo_propios": "true"}, headers=headers_usuario
    )

    assert nombres(response) == ["Mi press"]


def test_ejercicio_propio_solo_lo_ve_su_creador(
    client, headers_usuario, headers_otro_usuario
):
    creado = client.post("/ejercicios", json=nuevo("Secreto"), headers=headers_usuario)
    assert creado.status_code == 201
    assert creado.json()["es_base"] is False

    listado_otro = client.get("/ejercicios", headers=headers_otro_usuario)
    detalle_otro = client.get(
        f"/ejercicios/{creado.json()['id']}", headers=headers_otro_usuario
    )

    assert "Secreto" not in nombres(listado_otro)
    assert detalle_otro.status_code == 404


def test_trainer_tambien_puede_crear_ejercicios_propios(client, headers_trainer):
    response = client.post("/ejercicios", json=nuevo("Remo trainer"), headers=headers_trainer)

    assert response.status_code == 201


def test_no_se_puede_editar_ni_borrar_un_ejercicio_del_catalogo(
    client, db, headers_usuario
):
    base = crear_base(db, "Dominadas", GrupoMuscular.ESPALDA)

    editar = client.patch(
        f"/ejercicios/{base.id}", json={"nombre": "Otro nombre"}, headers=headers_usuario
    )
    borrar = client.delete(f"/ejercicios/{base.id}", headers=headers_usuario)

    assert editar.status_code == 403
    assert borrar.status_code == 403
    assert db.get(Ejercicio, base.id).nombre == "Dominadas"


def test_no_se_puede_editar_ni_borrar_el_ejercicio_de_otro_usuario(
    client, headers_usuario, headers_otro_usuario
):
    creado = client.post("/ejercicios", json=nuevo("Mío"), headers=headers_usuario).json()
    url = f"/ejercicios/{creado['id']}"

    editar = client.patch(url, json={"nombre": "Robado"}, headers=headers_otro_usuario)
    borrar = client.delete(url, headers=headers_otro_usuario)

    assert editar.status_code == 404
    assert borrar.status_code == 404
    original = client.get(url, headers=headers_usuario)
    assert original.json()["nombre"] == "Mío"


def test_editar_y_eliminar_un_ejercicio_propio(client, headers_usuario):
    creado = client.post("/ejercicios", json=nuevo("Viejo"), headers=headers_usuario).json()
    url = f"/ejercicios/{creado['id']}"

    editar = client.patch(
        url,
        json={"nombre": "Nuevo", "grupo_secundario": "TRICEPS"},
        headers=headers_usuario,
    )
    assert editar.status_code == 200
    assert editar.json()["nombre"] == "Nuevo"
    assert editar.json()["grupo_secundario"] == "TRICEPS"

    borrar = client.delete(url, headers=headers_usuario)
    assert borrar.status_code == 204
    assert client.get(url, headers=headers_usuario).status_code == 404


def test_nombre_repetido_devuelve_409(client, db, headers_usuario):
    crear_base(db, "Sentadilla", GrupoMuscular.CUADRICEPS)

    response = client.post(
        "/ejercicios", json=nuevo("sentadilla", "CUADRICEPS"), headers=headers_usuario
    )

    assert response.status_code == 409


def test_grupo_secundario_igual_al_principal_devuelve_422(client, headers_usuario):
    response = client.post(
        "/ejercicios",
        json=nuevo("Raro", "PECHO", grupo_secundario="PECHO"),
        headers=headers_usuario,
    )

    assert response.status_code == 422

def test_la_factory_conserva_tipo_de_medicion_y_uso_de_peso_corporal():
    from app.models.ejercicio import TipoMedicion

    datos = EjercicioCreate(
        nombre="Dominadas",
        grupo_principal=GrupoMuscular.ESPALDA,
        usa_peso_corporal=True,
    )
    ejercicio = EjercicioFactory.crear_base(datos)

    assert ejercicio.tipo_medicion == TipoMedicion.REPETICIONES
    assert ejercicio.usa_peso_corporal is True


def test_no_se_puede_combinar_peso_corporal_con_medicion_por_tiempo():
    import pytest
    from pydantic import ValidationError
    from app.models.ejercicio import TipoMedicion

    with pytest.raises(ValidationError):
        EjercicioCreate(
            nombre="Cinta",
            grupo_principal=GrupoMuscular.CARDIO,
            tipo_medicion=TipoMedicion.TIEMPO,
            usa_peso_corporal=True,
        )