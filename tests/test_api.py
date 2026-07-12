from fastapi.testclient import TestClient
from api.app import app


def test_root_endpoint():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "Portfolio Risk Alert API is running"
