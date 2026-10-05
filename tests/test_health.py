def test_health_responde_ok_y_conecta_con_la_base(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}

s