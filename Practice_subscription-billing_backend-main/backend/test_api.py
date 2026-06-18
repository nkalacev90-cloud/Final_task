from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
from models import User

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["message"] == "Сервер работает!"

def test_register():
    # Удаляем пользователя, если он уже есть
    db = SessionLocal()
    db.query(User).filter(User.email == "test@test.com").delete()
    db.commit()
    db.close()

    response = client.post("/register?email=test@test.com&password=123456")
    assert response.status_code == 200
    assert "user_id" in response.json()

def test_login():
    response = client.post(
        "/token",
        data={"username": "test@test.com", "password": "123456"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_get_tariffs_without_token():
    response = client.get("/tariffs")
    assert response.status_code == 401

def test_get_tariffs_with_token():
    login = client.post(
        "/token",
        data={"username": "test@test.com", "password": "123456"}
    )
    token = login.json()["access_token"]

    response = client.get(
        "/tariffs",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200