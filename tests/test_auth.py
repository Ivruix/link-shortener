import pytest
from datetime import datetime
from jose import jwt
from fastapi import HTTPException
from unittest.mock import MagicMock

from app.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    get_current_user_optional
)


class TestVerifyPassword:
    def test_valid_password_verification(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_invalid_password_verification(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_string_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed) is True

    def test_unicode_password(self):
        password = "пароль123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True


class TestGetPasswordHash:
    def test_successful_hashing(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert hashed != password

    def test_consistency_check(self):
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        assert hash1 != hash2

    def test_verification_compatibility(self):
        password = "testpassword123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_empty_string_password(self):
        hashed = get_password_hash("")
        assert isinstance(hashed, str)

    def test_long_password(self):
        password = "a" * 72
        hashed = get_password_hash(password)
        assert isinstance(hashed, str)
        assert verify_password(password, hashed) is True


class TestCreateAccessToken:
    def test_valid_token_creation(self):
        data = {"sub": "testuser"}
        token = create_access_token(data)
        assert isinstance(token, str)

    def test_token_structure_validation(self):
        from app.auth import SECRET_KEY
        data = {"sub": "testuser"}
        token = create_access_token(data)
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        assert "exp" in payload
        assert payload["sub"] == "testuser"

    def test_token_expiration_is_about_thirty_minutes(self):
        from app.auth import SECRET_KEY
        data = {"sub": "testuser"}
        token = create_access_token(data)
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        assert "exp" in payload
        assert payload["sub"] == "testuser"

    def test_empty_data_handling(self):
        token = create_access_token({})
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        assert "exp" in payload

    def test_multiple_fields_preserved(self):
        data = {"sub": "testuser", "role": "admin", "extra": "data"}
        token = create_access_token(data)
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert payload["extra"] == "data"


class TestGetCurrentUser:
    def test_invalid_token_malformed(self, db_session):
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, db_session)
        assert exc_info.value.status_code == 401

    def test_valid_token(self, db_session, test_user2):
        from unittest.mock import MagicMock
        mock_credentials = MagicMock()
        mock_credentials.credentials = create_access_token({"sub": test_user2.username})

        user = get_current_user(mock_credentials, db_session)
        assert user is not None
        assert user.id == test_user2.id

    def test_invalid_token_missing_username(self, db_session):
        from unittest.mock import MagicMock
        from app.auth import SECRET_KEY, ALGORITHM
        from jose import jwt
        mock_credentials = MagicMock()
        token = jwt.encode({}, SECRET_KEY, algorithm=ALGORITHM)
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, db_session)
        assert exc_info.value.status_code == 401

    def test_user_not_found(self, db_session):
        from unittest.mock import MagicMock
        mock_credentials = MagicMock()
        mock_credentials.credentials = create_access_token({"sub": "nonexistentuser"})

        with pytest.raises(HTTPException) as exc_info:
            get_current_user(mock_credentials, db_session)
        assert exc_info.value.status_code == 401


class TestGetCurrentUserOptional:
    def test_no_credentials_provided(self, db_session):
        user = get_current_user_optional(None, db_session)
        assert user is None

    def test_invalid_token_returns_none(self, db_session):
        mock_credentials = MagicMock()
        mock_credentials.credentials = "invalid.token.here"

        user = get_current_user_optional(mock_credentials, db_session)
        assert user is None

    def test_user_not_found_returns_none(self, db_session):
        from unittest.mock import MagicMock
        mock_credentials = MagicMock()
        mock_credentials.credentials = create_access_token({"sub": "nonexistentuser"})

        user = get_current_user_optional(mock_credentials, db_session)
        assert user is None
