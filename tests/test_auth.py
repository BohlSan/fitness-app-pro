from sqlalchemy import select

from app.models.usuario import Usuario

PASSWORD = "secreta123"


def registrar(client, email="ana@example.com", rol="USUARIO", password=PASSWORD):
    return client.post(
        "/auth/registro",
        json={"nombre": "Ana", "email": email, "password": password, "rol": rol},
    )


def encabezado(token):
    return {"Authorization": f"Bearer {token}"}


def test_registro_exitoso_devuelve_token_y_usuario(client):
    response = registrar(client)

    assert response.status_code == 201
    cuerpo = response.json()
    assert cuerpo["access_token"]
    assert cuerpo["usuario"]["email"] == "ana@example.com"
    assert cuerpo["usuario"]["rol"] == "USUARIO"
    assert "password" not in cuerpo["usuario"]
    assert "password_hash" not in cuerpo["usuario"]


def test_password_se_guarda_hasheada(client, db):
    registrar(client)

    usuario = db.scalar(select(Usuario).where(Usuario.email == "ana@example.com"))
    assert usuario.password_hash != PASSWORD
    assert usuario.password_hash.startswith("$2")


def test_registro_con_email_duplicado_devuelve_409(client):
    registrar(client)
    response = registrar(client)

    assert response.status_code == 409


def test_registro_con_password_corta_devuelve_422(client):
    response = registrar(client, password="corta")

    assert response.status_code == 422


def test_login_correcto_permite_acceder_a_me(client):
    registrar(client)

    login = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": PASSWORD}
    )
    assert login.status_code == 200

    me = client.get("/auth/me", headers=encabezado(login.json()["access_token"]))
    assert me.status_code == 200
    assert me.json()["email"] == "ana@example.com"


def test_login_con_password_incorrecta_devuelve_401(client):
    registrar(client)

    response = client.post(
        "/auth/login", json={"email": "ana@example.com", "password": "incorrecta1"}
    )

    assert response.status_code == 401


def test_me_sin_token_devuelve_401(client):
    response = client.get("/auth/me")

    assert response.status_code == 401


def test_usuario_particular_no_accede_al_panel_de_trainer(client):
    token = registrar(client, rol="USUARIO").json()["access_token"]

    response = client.get("/trainer/panel", headers=encabezado(token))

    assert response.status_code == 403


def test_trainer_accede_al_panel_de_trainer(client):
    token = registrar(client, email="leo@example.com", rol="PERSONAL_TRAINER").json()[
        "access_token"
    ]

    response = client.get("/trainer/panel", headers=encabezado(token))

    assert response.status_code == 200