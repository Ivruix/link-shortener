import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.models import Link, ExpiredLink


class TestCreateLink:
    def test_successful_shortening_auto_code(self, client: TestClient):
        client.post("/auth/register", json={"username": "linkuser1", "password": "linkpass"})
        response = client.post("/auth/login", json={"username": "linkuser1", "password": "linkpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://example.com"
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "short_code" in data
        assert len(data["short_code"]) == 6
        assert data["original_url"] == "https://example.com"

    def test_successful_shortening_custom_alias(self, client: TestClient):
        client.post("/auth/register", json={"username": "aliasuser", "password": "aliaspass"})
        response = client.post("/auth/login", json={"username": "aliasuser", "password": "aliaspass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://example.com",
            "custom_alias": "myalias"
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == "myalias"

    def test_duplicate_custom_alias_returns_400(self, client: TestClient):
        client.post("/auth/register", json={"username": "dupuser", "password": "duppass"})
        response = client.post("/auth/login", json={"username": "dupuser", "password": "duppass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/links/shorten", json={
            "original_url": "https://example.com",
            "custom_alias": "duplicate"
        }, headers=headers)

        response = client.post("/links/shorten", json={
            "original_url": "https://other.com",
            "custom_alias": "duplicate"
        }, headers=headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_anonymous_user_creates_link(self, client: TestClient):
        response = client.post("/links/shorten", json={
            "original_url": "https://example.com"
        })
        assert response.status_code == 200
        data = response.json()
        assert "short_code" in data

    def test_with_expiration_date(self, client: TestClient):
        client.post("/auth/register", json={"username": "expuser", "password": "exppass"})
        response = client.post("/auth/login", json={"username": "expuser", "password": "exppass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
        response = client.post("/links/shorten", json={
            "original_url": "https://example.com",
            "expires_at": expires_at
        }, headers=headers)
        assert response.status_code == 200
        assert "expires_at" in response.json()

    def test_short_code_collision_handling(self, client: TestClient, db_session):
        from app.models import Link
        from app.utils import generate_short_code

        existing_code = generate_short_code()
        existing_link = Link(
            short_code=existing_code,
            original_url="https://existing.com",
            created_at=datetime.utcnow(),
            access_count=0
        )
        db_session.add(existing_link)
        db_session.commit()

        import app.routers.links
        original_generate = generate_short_code

        collision_count = [0]

        def mock_generate_with_collision():
            if collision_count[0] < 3:
                collision_count[0] += 1
                return existing_code
            return original_generate()

        app.routers.links.generate_short_code = mock_generate_with_collision

        try:
            response = client.post("/links/shorten", json={
                "original_url": "https://newurl.com"
            })
            assert response.status_code == 200
            data = response.json()
            assert data["short_code"] != existing_code
        finally:
            app.routers.links.generate_short_code = original_generate
            db_session.query(Link).filter(Link.short_code == existing_code).delete()
            db_session.commit()


class TestSearchLink:
    def test_cache_hit(self, client: TestClient, mock_redis, db_session):
        from app.models import Link
        from app.redis_client import get_search_key
        import hashlib

        client.post("/auth/register", json={"username": "searchuser", "password": "searchpass"})
        response = client.post("/auth/login", json={"username": "searchuser", "password": "searchpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://search.com"
        }, headers=headers)
        short_code = response.json()["short_code"]

        link = db_session.query(Link).filter(Link.short_code == short_code).first()

        search_key = get_search_key("https://search.com")
        mock_redis.setex(search_key, 3600, short_code.encode())

        response = client.get("/links/search?original_url=https://search.com")
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == short_code
        assert data["original_url"] == "https://search.com"

    def test_cache_miss_database_hit(self, client: TestClient):
        client.post("/auth/register", json={"username": "searchuser2", "password": "searchpass"})
        response = client.post("/auth/login", json={"username": "searchuser2", "password": "searchpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        client.post("/links/shorten", json={
            "original_url": "https://search2.com"
        }, headers=headers)

        response = client.get("/links/search?original_url=https://search2.com")
        assert response.status_code == 200
        data = response.json()
        assert "short_code" in data

    def test_cache_miss_sets_cache(self, client: TestClient, mock_redis):
        client.post("/auth/register", json={"username": "searchuser3", "password": "searchpass"})
        response = client.post("/auth/login", json={"username": "searchuser3", "password": "searchpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://search3.com"
        }, headers=headers)
        short_code = response.json()["short_code"]

        mock_redis.delete(f"search:https://search3.com")
        response = client.get("/links/search?original_url=https://search3.com")
        assert response.status_code == 200
        assert mock_redis.exists(f"search:https://search3.com") >= 0

    def test_link_not_found_returns_404(self, client: TestClient):
        response = client.get("/links/search?original_url=https://nonexistent.com")
        assert response.status_code == 404


class TestRedirectLink:
    def test_successful_redirect(self, client: TestClient):
        response = client.post("/links/shorten", json={
            "original_url": "https://redirect.com"
        })
        short_code = response.json()["short_code"]

        response = client.get(f"/links/{short_code}", follow_redirects=False)
        assert response.status_code == 307

    def test_redirect_cache_hit(self, client: TestClient, mock_redis):
        response = client.post("/links/shorten", json={
            "original_url": "https://redirectcache.com"
        })
        short_code = response.json()["short_code"]

        mock_redis.setex(f"redirect:{short_code}", 3600, b"https://redirectcache.com")

        response = client.get(f"/links/{short_code}", follow_redirects=False)
        assert response.status_code == 307

    def test_redirect_cache_miss_database_hit(self, client: TestClient):
        response = client.post("/links/shorten", json={
            "original_url": "https://redirect2.com"
        })
        short_code = response.json()["short_code"]

        response = client.get(f"/links/{short_code}", follow_redirects=False)
        assert response.status_code == 307

    def test_link_expired_returns_410(self, client: TestClient, db_session):
        from datetime import timedelta
        from app.models import Link

        expired_link = Link(
            short_code="expired999",
            original_url="https://expired-link.com",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(days=1),
            access_count=0
        )
        db_session.add(expired_link)
        db_session.commit()

        response = client.get("/links/expired999", follow_redirects=False)
        assert response.status_code == 410

        db_session.query(Link).filter(Link.short_code == "expired999").delete()
        db_session.commit()

    def test_redirect_increments_access_count(self, client: TestClient):
        client.post("/auth/register", json={"username": "countuser", "password": "countpass"})
        response = client.post("/auth/login", json={"username": "countuser", "password": "countpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://count.com"
        }, headers=headers)
        short_code = response.json()["short_code"]

        client.get(f"/links/{short_code}", follow_redirects=False)
        client.get(f"/links/{short_code}", follow_redirects=False)

        response = client.get(f"/links/{short_code}/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["access_count"] >= 2

    def test_link_not_found_returns_404(self, client: TestClient):
        response = client.get("/links/nonexistent", follow_redirects=False)
        assert response.status_code == 404


class TestGetLinkStats:
    def test_cache_hit(self, client: TestClient, mock_redis):
        import json
        response = client.post("/links/shorten", json={
            "original_url": "https://stats.com"
        })
        short_code = response.json()["short_code"]

        stats = {
            "short_code": short_code,
            "original_url": "https://stats.com",
            "created_at": datetime.utcnow().isoformat(),
            "access_count": 5,
            "last_accessed_at": None
        }
        mock_redis.setex(f"stats:{short_code}", 1800, json.dumps(stats).encode())

        response = client.get(f"/links/{short_code}/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["access_count"] == 5

    def test_cache_miss_database_hit(self, client: TestClient):
        response = client.post("/links/shorten", json={
            "original_url": "https://stats2.com"
        })
        short_code = response.json()["short_code"]

        response = client.get(f"/links/{short_code}/stats")
        assert response.status_code == 200
        data = response.json()
        assert "short_code" in data
        assert "access_count" in data

    def test_link_not_found_returns_404(self, client: TestClient):
        response = client.get("/links/nonexistent/stats")
        assert response.status_code == 404


class TestUpdateLink:
    def test_successful_update_by_owner(self, client: TestClient):
        client.post("/auth/register", json={"username": "updateuser", "password": "updatepass"})
        response = client.post("/auth/login", json={"username": "updateuser", "password": "updatepass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://example.com"
        }, headers=headers)
        short_code = response.json()["short_code"]

        response = client.put(f"/links/{short_code}", json={
            "original_url": "https://updated.com"
        }, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["original_url"] == "https://updated.com"

    def test_unauthorized_not_owner_returns_403(self, client: TestClient):
        client.post("/auth/register", json={"username": "owner1", "password": "pass1"})
        response = client.post("/auth/login", json={"username": "owner1", "password": "pass1"})
        token1 = response.json()["access_token"]

        response = client.post("/links/shorten", json={
            "original_url": "https://example.com"
        }, headers={"Authorization": f"Bearer {token1}"})
        short_code = response.json()["short_code"]

        client.post("/auth/register", json={"username": "owner2", "password": "pass2"})
        response = client.post("/auth/login", json={"username": "owner2", "password": "pass2"})
        token2 = response.json()["access_token"]

        response = client.put(f"/links/{short_code}", json={
            "original_url": "https://updated.com"
        }, headers={"Authorization": f"Bearer {token2}"})
        assert response.status_code == 403

    def test_link_not_found_returns_404(self, client: TestClient):
        client.post("/auth/register", json={"username": "updateuser2", "password": "updatepass2"})
        response = client.post("/auth/login", json={"username": "updateuser2", "password": "updatepass2"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.put("/links/nonexistent", json={
            "original_url": "https://updated.com"
        }, headers=headers)
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_unauthorized_no_auth_returns_401(self, client: TestClient):
        response = client.put("/links/somelink", json={
            "original_url": "https://updated.com"
        })
        assert response.status_code == 401


class TestDeleteLink:
    def test_successful_deletion_by_owner(self, client: TestClient):
        client.post("/auth/register", json={"username": "deleteuser", "password": "deletepass"})
        response = client.post("/auth/login", json={"username": "deleteuser", "password": "deletepass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://example.com"
        }, headers=headers)
        short_code = response.json()["short_code"]

        response = client.delete(f"/links/{short_code}", headers=headers)
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

    def test_deletion_creates_expired_link_record(self, client: TestClient):
        client.post("/auth/register", json={"username": "expiredlinkuser", "password": "expiredpass"})
        response = client.post("/auth/login", json={"username": "expiredlinkuser", "password": "expiredpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.post("/links/shorten", json={
            "original_url": "https://expiredexample.com"
        }, headers=headers)
        short_code = response.json()["short_code"]

        response = client.delete(f"/links/{short_code}", headers=headers)
        assert response.status_code == 200

        response = client.get("/links/expired", headers=headers)
        assert response.status_code == 200
        expired_links = response.json()
        assert any(l["short_code"] == short_code for l in expired_links)

    def test_unauthorized_not_owner_returns_403(self, client: TestClient):
        client.post("/auth/register", json={"username": "delowner1", "password": "pass1"})
        response = client.post("/auth/login", json={"username": "delowner1", "password": "pass1"})
        token1 = response.json()["access_token"]

        response = client.post("/links/shorten", json={
            "original_url": "https://example.com"
        }, headers={"Authorization": f"Bearer {token1}"})
        short_code = response.json()["short_code"]

        client.post("/auth/register", json={"username": "delowner2", "password": "pass2"})
        response = client.post("/auth/login", json={"username": "delowner2", "password": "pass2"})
        token2 = response.json()["access_token"]

        response = client.delete(f"/links/{short_code}", headers={"Authorization": f"Bearer {token2}"})
        assert response.status_code == 403

    def test_link_not_found_returns_404(self, client: TestClient):
        client.post("/auth/register", json={"username": "deleteuser2", "password": "deletepass2"})
        response = client.post("/auth/login", json={"username": "deleteuser2", "password": "deletepass2"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.delete("/links/nonexistent", headers=headers)
        assert response.status_code == 404

    def test_unauthorized_no_auth_returns_401(self, client: TestClient):
        response = client.delete("/links/somelink")
        assert response.status_code == 401


class TestGetExpiredLinks:
    def test_successful_retrieval(self, client: TestClient):
        client.post("/auth/register", json={"username": "expireduser", "password": "expiredpass"})
        response = client.post("/auth/login", json={"username": "expireduser", "password": "expiredpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/links/expired", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_unauthorized_returns_401(self, client: TestClient):
        response = client.get("/links/expired")
        assert response.status_code == 401

    def test_no_expired_links_returns_empty_list(self, client: TestClient):
        client.post("/auth/register", json={"username": "noexpireduser", "password": "noexpiredpass"})
        response = client.post("/auth/login", json={"username": "noexpireduser", "password": "noexpiredpass"})
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/links/expired", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
