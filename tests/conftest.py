import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import fakeredis
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from app.database import Base, get_db
from app.models import User, Link, ExpiredLink
from app.auth import get_password_hash, create_access_token
from app import models

import tempfile

SQLALCHEMY_DATABASE_URL = "sqlite:///test.db"

test_engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session")
def engine():
    return test_engine


@pytest.fixture(scope="function")
def db_session(engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_user(db_session):
    user = User(username="testuser", hashed_password=get_password_hash("testpass"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_user2(db_session):
    user = User(username="testuser2", hashed_password=get_password_hash("testpass2"))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_link(db_session, test_user):
    link = Link(
        short_code="abc123",
        original_url="https://example.com",
        user_id=test_user.id,
        created_at=datetime.utcnow(),
        access_count=0
    )
    db_session.add(link)
    db_session.commit()
    db_session.refresh(link)
    return link


@pytest.fixture
def test_expired_link(db_session, test_user):
    expired_link = ExpiredLink(
        short_code="expired123",
        original_url="https://expired.com",
        user_id=test_user.id,
        created_at=datetime.utcnow() - timedelta(days=10),
        expired_at=datetime.utcnow(),
        deletion_reason="manual"
    )
    db_session.add(expired_link)
    db_session.commit()
    db_session.refresh(expired_link)
    return expired_link


@pytest.fixture
def test_token(test_user):
    return create_access_token(data={"sub": test_user.username})


@pytest.fixture
def auth_headers(test_token):
    return {"Authorization": f"Bearer {test_token}"}


@pytest.fixture
def mock_redis():
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=False)
    return fake_redis


@pytest.fixture(scope="function")
def client(mock_redis, engine):
    from fastapi import FastAPI
    from app.routers import auth, links
    from app.main import root
    from sqlalchemy.orm import sessionmaker
    import os

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            pass

    test_app = FastAPI(title="Test Link Shortener")
    test_app.include_router(auth.router)
    test_app.include_router(links.router)
    test_app.get("/")(root)
    test_app.dependency_overrides[get_db] = override_get_db

    import app.routers.links
    original_redis = app.routers.links.redis_client
    app.routers.links.redis_client = mock_redis

    with TestClient(test_app) as test_client:
        yield test_client

    test_app.dependency_overrides.clear()
    app.routers.links.redis_client = original_redis

    db = TestingSessionLocal()
    db.query(User).delete()
    db.query(Link).delete()
    db.query(ExpiredLink).delete()
    db.commit()
    db.close()


@pytest.fixture(scope="function")
def client_with_db(mock_redis, engine):
    from fastapi import FastAPI
    from app.routers import auth, links
    from sqlalchemy.orm import sessionmaker
    import os

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            pass

    test_app = FastAPI(title="Test Link Shortener")
    test_app.include_router(auth.router)
    test_app.include_router(links.router)
    test_app.dependency_overrides[get_db] = override_get_db

    import app.routers.links
    original_redis = app.routers.links.redis_client
    app.routers.links.redis_client = mock_redis

    with TestClient(test_app) as test_client:
        yield test_client, TestingSessionLocal

    test_app.dependency_overrides.clear()
    app.routers.links.redis_client = original_redis

    db = TestingSessionLocal()
    db.query(User).delete()
    db.query(Link).delete()
    db.query(ExpiredLink).delete()
    db.commit()
    db.close()
