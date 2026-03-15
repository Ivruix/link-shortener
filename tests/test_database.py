import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db, engine, SessionLocal


class TestDatabase:
    def test_engine_is_created(self):
        assert engine is not None

    def test_base_metadata_exists(self):
        assert hasattr(Base, 'metadata')

    def test_session_local_is_sessionmaker(self):
        assert isinstance(SessionLocal, sessionmaker)

    def test_get_db_yields_session(self):
        gen = get_db()
        db = next(gen)
        assert db is not None
        db.close()

    def test_get_db_closes_session_on_exception(self):
        gen = get_db()
        db = next(gen)
        with pytest.raises(Exception):
            gen.throw(Exception)
        assert db is not None
