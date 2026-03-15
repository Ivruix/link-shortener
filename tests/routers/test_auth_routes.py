import pytest
from fastapi.testclient import TestClient
from jose import jwt


class TestRegister:
    def test_successful_registration(self, client: TestClient):
        response = client.post("/auth/register", json={
            "username": "newuser",
            "password": "newpass123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_duplicate_username_returns_400(self, client: TestClient):
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "password123"
        })
        assert response.status_code in (200, 400)

        if response.status_code == 200:
            response = client.post("/auth/register", json={
                "username": "testuser",
                "password": "password123"
            })
            assert response.status_code == 400
            assert response.json()["detail"] == "Username already exists"

    def test_invalid_data_missing_username(self, client: TestClient):
        response = client.post("/auth/register", json={
            "password": "password123"
        })
        assert response.status_code == 422

    def test_invalid_data_missing_password(self, client: TestClient):
        response = client.post("/auth/register", json={
            "username": "testuser"
        })
        assert response.status_code == 422

    def test_token_contains_correct_username(self, client: TestClient):
        response = client.post("/auth/register", json={
            "username": "tokenuser",
            "password": "tokenpass123"
        })
        assert response.status_code == 200

        token = response.json()["access_token"]
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "tokenuser"


class TestLogin:
    def test_successful_login(self, client: TestClient):
        client.post("/auth/register", json={
            "username": "loginuser",
            "password": "loginpass"
        })

        response = client.post("/auth/login", json={
            "username": "loginuser",
            "password": "loginpass"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_invalid_username_returns_401(self, client: TestClient):
        response = client.post("/auth/login", json={
            "username": "nonexistent",
            "password": "password"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"

    def test_invalid_password_returns_401(self, client: TestClient):
        client.post("/auth/register", json={
            "username": "wrongpassuser",
            "password": "correctpass"
        })

        response = client.post("/auth/login", json={
            "username": "wrongpassuser",
            "password": "wrongpassword"
        })
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid username or password"

    def test_missing_username_returns_422(self, client: TestClient):
        response = client.post("/auth/login", json={
            "password": "password"
        })
        assert response.status_code == 422

    def test_missing_password_returns_422(self, client: TestClient):
        response = client.post("/auth/login", json={
            "username": "testuser"
        })
        assert response.status_code == 422

    def test_token_verification(self, client: TestClient):
        client.post("/auth/register", json={
            "username": "tokenverify",
            "password": "tokenpass"
        })

        response = client.post("/auth/login", json={
            "username": "tokenverify",
            "password": "tokenpass"
        })
        assert response.status_code == 200

        token = response.json()["access_token"]
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "tokenverify"
