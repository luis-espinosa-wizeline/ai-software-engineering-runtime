from fastapi.testclient import TestClient

from app.main import app


def test_read_runtime_info() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "name": "AI Software Engineering Runtime",
        "version": "0.1.0",
    }

