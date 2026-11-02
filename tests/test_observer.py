from app.services.eventos import Sujeto
from app.services.fechas import hoy


class Espia:
    def __init__(self):
        self.eventos = []

    def actualizar(self, evento):
        self.eventos.append(evento)


def vinculo_activo(client, headers_trainer, headers_cliente):
    codigo = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    vinculo_id = client.post("/vinculo", json={"codigo": codigo}, headers=headers_cliente).json()["vinculo_id"]
    client.post(f"/trainer/vinculos/{vinculo_id}/aceptar", headers=headers_trainer)
    return vinculo_id


def test_el_sujeto_notifica_a_los_observadores_suscritos():
    sujeto = Sujeto()
    a, b = Espia(), Espia()
    sujeto.suscribir(a)
    sujeto.suscribir(b)
    sujeto.suscribir(a)  # suscribirse dos veces no duplica las notificaciones

    sujeto.notificar("primero")
    sujeto.desuscribir(b)
    sujeto.notificar("segundo")

    assert a.eventos == ["primero", "segundo"]
    assert b.eventos == ["primero"]


def test_el_trainer_recibe_una_novedad_cuando_su_cliente_termina_un_entrenamiento(
    client, ejercicios, entrenar, headers_trainer, headers_usuario
):
    vinculo_activo(client, headers_trainer, headers_usuario)

    entrenar(headers_usuario, ejercicios[0], hoy())

    novedades = client.get("/trainer/actividad", headers=headers_trainer).json()
    assert len(novedades) == 1
    novedad = novedades[0]
    assert novedad["tipo"] == "ENTRENAMIENTO_FINALIZADO"
    assert novedad["cliente"]["email"] == "usuario@example.com"
    assert novedad["titulo"] == "Estilo libre"
    assert novedad["volumen_kg"] == 600.0
    assert novedad["leida"] is False
    assert client.get("/trainer/panel", headers=headers_trainer).json()["actividad_sin_leer"] == 1

    client.post("/trainer/actividad/leidas", headers=headers_trainer)

    assert client.get("/trainer/panel", headers=headers_trainer).json()["actividad_sin_leer"] == 0
    assert client.get("/trainer/actividad", headers=headers_trainer).json()[0]["leida"] is True


def test_sin_una_relacion_activa_no_se_generan_novedades(
    client, ejercicios, entrenar, headers_trainer, headers_usuario
):
    # Solicitud todavía pendiente: el trainer no recibe nada
    codigo = client.get("/trainer/codigo", headers=headers_trainer).json()["codigo_enlace"]
    client.post("/vinculo", json={"codigo": codigo}, headers=headers_usuario)

    entrenar(headers_usuario, ejercicios[0], hoy())

    assert client.get("/trainer/actividad", headers=headers_trainer).json() == []


def test_las_novedades_son_privadas_de_cada_trainer(
    client, ejercicios, entrenar, headers_trainer, headers_otro_trainer, headers_usuario
):
    vinculo_activo(client, headers_trainer, headers_usuario)

    entrenar(headers_usuario, ejercicios[0], hoy())

    assert len(client.get("/trainer/actividad", headers=headers_trainer).json()) == 1
    assert client.get("/trainer/actividad", headers=headers_otro_trainer).json() == []