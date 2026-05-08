from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_get_user_returns_known_user() -> None:
    response = client.get("/users/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "email": "ada@example.com",
        "name": "Ada Lovelace",
    }


def test_invalid_user_id_returns_400() -> None:
    response = client.get("/users/0")

    assert response.status_code == 400
    assert response.json()["detail"] == "User id must be positive"


def test_missing_user_returns_404() -> None:
    response = client.get("/users/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_empty_email_returns_422() -> None:
    response = client.post("/users", json={"email": " ", "name": "New User"})

    assert response.status_code == 422


def test_create_user_returns_created_user() -> None:
    response = client.post(
        "/users",
        json={"email": "katherine@example.com", "name": "Katherine Johnson"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "katherine@example.com"
    assert body["name"] == "Katherine Johnson"
    assert isinstance(body["id"], int)
