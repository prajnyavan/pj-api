from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_missing_token_returns_401() -> None:
    response = client.get("/auth/validate")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization token"


def test_invalid_token_returns_401() -> None:
    response = client.get("/auth/validate", headers={"Authorization": "Bearer bad-token"})

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid authorization token"


def test_valid_token_authenticates() -> None:
    response = client.get("/auth/validate", headers={"Authorization": "Bearer valid-token"})

    assert response.status_code == 200
    assert response.json() == {"status": "authenticated"}
