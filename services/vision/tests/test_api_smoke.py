import os
os.environ.setdefault("CV_BACKEND", "mock")
os.environ.setdefault("CAMERA_SOURCE", "mock")
os.environ.setdefault("CV_DB_ENABLED", "false")
from fastapi.testclient import TestClient
from elevator_vision.api import app

def test_health_and_status():
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        data = client.get("/api/cv/status").json()
        assert data["backend"] == "mock"
