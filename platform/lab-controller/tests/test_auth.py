"""
Tests for the authentication system.

Covers:
  T-A1: Password hashing round-trip
  T-A2: JWT creation, decoding, and expiry
  T-A3: Registration endpoint
  T-A4: Login endpoint
  T-A5: Token refresh
  T-A6: Protected endpoint access
  T-A7: Role-based access control
"""

import pytest
import os
import sys
import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# T-A1: Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_and_verify(self):
        from app.services.auth_service import hash_password, verify_password
        hashed = hash_password("my-secret-password")
        assert hashed != "my-secret-password"
        assert verify_password("my-secret-password", hashed)

    def test_wrong_password_fails(self):
        from app.services.auth_service import hash_password, verify_password
        hashed = hash_password("correct-password")
        assert not verify_password("wrong-password", hashed)


# ---------------------------------------------------------------------------
# T-A2: JWT tokens
# ---------------------------------------------------------------------------

class TestJWTTokens:
    def test_create_and_decode_access_token(self):
        from app.services.auth_service import create_access_token, decode_token
        token = create_access_token("user-123", "learner")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["role"] == "learner"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        from app.services.auth_service import create_refresh_token, decode_token
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_invalid_token_returns_none(self):
        from app.services.auth_service import decode_token
        assert decode_token("garbage-token") is None

    def test_expired_token_returns_none(self):
        from app.services.auth_service import decode_token
        from jose import jwt
        from app.schemas import settings
        expired_payload = {
            "sub": "user-789",
            "type": "access",
            "exp": datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
        }
        token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        assert decode_token(token) is None


# ---------------------------------------------------------------------------
# T-A3 through T-A7: Endpoint tests via TestClient
# ---------------------------------------------------------------------------

class TestAuthEndpoints:
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Patch the database to use in-memory SQLite for each test."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool
        from app.database import Base, get_db
        from app.main import app
        from fastapi.testclient import TestClient

        # StaticPool ensures all connections share the same in-memory database
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestSession = sessionmaker(bind=engine)

        def override_get_db():
            db = TestSession()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)
        self.engine = engine
        self.TestSession = TestSession
        yield
        app.dependency_overrides.clear()

    def _register(self, username="testuser", password="testpassword123"):
        return self.client.post("/api/auth/register", json={
            "username": username, "password": password
        })

    def test_register_success(self):
        resp = self._register()
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "testuser"
        assert data["user"]["role"] == "learner"

    def test_register_duplicate_username(self):
        self._register()
        resp = self._register()
        assert resp.status_code == 409

    def test_register_short_password(self):
        resp = self.client.post("/api/auth/register", json={
            "username": "testuser", "password": "short"
        })
        assert resp.status_code == 422

    def test_login_success(self):
        self._register()
        resp = self.client.post("/api/auth/login", json={
            "username": "testuser", "password": "testpassword123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["username"] == "testuser"

    def test_login_wrong_password(self):
        self._register()
        resp = self.client.post("/api/auth/login", json={
            "username": "testuser", "password": "wrongpassword"
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = self.client.post("/api/auth/login", json={
            "username": "nobody", "password": "whatever123"
        })
        assert resp.status_code == 401

    def test_refresh_token(self):
        reg = self._register()
        refresh_token = reg.json()["refresh_token"]
        resp = self.client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_with_invalid_token(self):
        resp = self.client.post("/api/auth/refresh", json={
            "refresh_token": "garbage"
        })
        assert resp.status_code == 401

    def test_me_with_valid_token(self):
        reg = self._register()
        token = reg.json()["access_token"]
        resp = self.client.get("/api/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    def test_me_without_token(self):
        resp = self.client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self):
        resp = self.client.get("/api/auth/me", headers={
            "Authorization": "Bearer garbage-token"
        })
        assert resp.status_code == 401

    def test_admin_endpoint_denied_for_learner(self):
        """Admin-protected endpoints should reject learner users."""
        # Register as learner (default)
        reg = self._register()
        token = reg.json()["access_token"]

        # The admin router uses require_admin — test via /lab/admin endpoints
        resp = self.client.post(
            "/lab/admin/reset/env-test",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Admin endpoints still use verify_api_key, not JWT yet — so this returns 422 (missing X-API-Key)
        # This test documents the current state; will be updated when admin switches to JWT
        assert resp.status_code == 422
