from fastapi.testclient import TestClient

import elevator_gateway.app as gateway_app
from elevator_gateway.security import hash_password, verify_password


def test_health_shape(monkeypatch):
    monkeypatch.setattr(gateway_app, "service_available", lambda url: url.endswith("/health"))
    client = TestClient(gateway_app.app)
    data = client.get("/health").json()
    assert data == {"status": "ok", "service": "gateway", "agent": True, "vision": True}


def test_password_round_trip():
    encoded = hash_password("strong-password")
    assert verify_password("strong-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_chat_proxy(monkeypatch):
    def fake_request(method, url, **kwargs):
        assert method == "POST"
        assert url.endswith("/chat")
        assert kwargs["json"]["message"] == "hello"
        return {"answer": "ok"}

    monkeypatch.setattr(gateway_app, "request_json", fake_request)
    client = TestClient(gateway_app.app)
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 200
    assert response.json()["answer"] == "ok"
