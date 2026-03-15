import pytest


class TestRootEndpoint:
    def test_root_endpoint_returns_message(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Link Shortener API"
