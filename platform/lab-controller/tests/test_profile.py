"""
Tests for the profile API.

Covers:
  T-P1: Profile CRUD (get, save result, export)
  T-P2: Profile import with merge strategy
  T-P3: Auth required for profile endpoints
"""

import pytest
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, User, Profile, get_db
from app.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def auth_client():
    """TestClient with in-memory DB and a pre-registered user."""
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
    client = TestClient(app)

    # Register a user
    resp = client.post("/api/auth/register", json={
        "username": "profuser", "password": "testpassword123"
    })
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    yield client, headers, TestSession

    app.dependency_overrides.clear()


class TestProfileCRUD:
    def test_get_empty_profile(self, auth_client):
        client, headers, _ = auth_client
        resp = client.get("/api/profile", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["domains"] == {}

    def test_save_result(self, auth_client):
        client, headers, _ = auth_client
        resp = client.post("/api/profile/result", headers=headers, json={
            "scenario_id": "d01-test-scenario",
            "domain": 1,
            "domain_name": "Scripting & Automation",
            "level": 3,
            "confidence": "high",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "1" in data["domains"]
        assert len(data["domains"]["1"]["results"]) == 1
        assert data["domains"]["1"]["results"][0]["level"] == 3

    def test_save_result_replaces_existing(self, auth_client):
        client, headers, _ = auth_client
        # Save first result
        client.post("/api/profile/result", headers=headers, json={
            "scenario_id": "d01-test-scenario", "domain": 1,
            "domain_name": "Scripting", "level": 2,
        })
        # Save again — should replace
        client.post("/api/profile/result", headers=headers, json={
            "scenario_id": "d01-test-scenario", "domain": 1,
            "domain_name": "Scripting", "level": 4,
        })
        resp = client.get("/api/profile", headers=headers)
        results = resp.json()["domains"]["1"]["results"]
        assert len(results) == 1
        assert results[0]["level"] == 4

    def test_export_profile(self, auth_client):
        client, headers, _ = auth_client
        client.post("/api/profile/result", headers=headers, json={
            "scenario_id": "d01-test", "domain": 1,
            "domain_name": "Scripting", "level": 3,
        })
        resp = client.get("/api/profile/export", headers=headers)
        assert resp.status_code == 200
        assert "1" in resp.json()["domains"]


class TestProfileImport:
    def test_import_empty_server(self, auth_client):
        """Import into empty server profile — should adopt all incoming data."""
        client, headers, _ = auth_client
        incoming = {
            "updated": "2026-01-01T00:00:00Z",
            "domains": {
                "1": {
                    "domain_name": "Scripting",
                    "results": [
                        {"scenario_id": "d01-a", "level": 2, "created_at": "2026-01-01T10:00:00Z"},
                        {"scenario_id": "d01-b", "level": 3, "created_at": "2026-01-01T11:00:00Z"},
                    ]
                }
            }
        }
        resp = client.post("/api/profile/import", headers=headers, json={"profile": incoming})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["domains"]["1"]["results"]) == 2

    def test_import_merge_most_recent_wins(self, auth_client):
        """When server has a result and import has a newer one, import wins."""
        client, headers, _ = auth_client
        # Save server result (older)
        client.post("/api/profile/result", headers=headers, json={
            "scenario_id": "d01-a", "domain": 1, "domain_name": "Scripting", "level": 2,
        })
        # Import with a newer result
        incoming = {
            "domains": {
                "1": {
                    "domain_name": "Scripting",
                    "results": [
                        {"scenario_id": "d01-a", "level": 4, "created_at": "2099-01-01T00:00:00Z"},
                    ]
                }
            }
        }
        resp = client.post("/api/profile/import", headers=headers, json={"profile": incoming})
        data = resp.json()
        results = data["domains"]["1"]["results"]
        # Should have the imported result (level 4, newer timestamp)
        d01_a = [r for r in results if r["scenario_id"] == "d01-a"]
        assert len(d01_a) == 1
        assert d01_a[0]["level"] == 4

    def test_import_merge_server_wins_if_newer(self, auth_client):
        """When server result is newer than import, server result is kept."""
        client, headers, _ = auth_client
        # Save server result (will have a recent timestamp)
        client.post("/api/profile/result", headers=headers, json={
            "scenario_id": "d01-a", "domain": 1, "domain_name": "Scripting", "level": 3,
        })
        # Import with an older result
        incoming = {
            "domains": {
                "1": {
                    "domain_name": "Scripting",
                    "results": [
                        {"scenario_id": "d01-a", "level": 1, "created_at": "2020-01-01T00:00:00Z"},
                    ]
                }
            }
        }
        resp = client.post("/api/profile/import", headers=headers, json={"profile": incoming})
        data = resp.json()
        results = data["domains"]["1"]["results"]
        d01_a = [r for r in results if r["scenario_id"] == "d01-a"]
        assert len(d01_a) == 1
        assert d01_a[0]["level"] == 3  # server's result preserved


class TestProfileAuth:
    def test_get_profile_unauthenticated(self, auth_client):
        client, _, _ = auth_client
        resp = client.get("/api/profile")
        assert resp.status_code == 401

    def test_save_result_unauthenticated(self, auth_client):
        client, _, _ = auth_client
        resp = client.post("/api/profile/result", json={
            "scenario_id": "d01-test", "domain": 1, "level": 2,
        })
        assert resp.status_code == 401
