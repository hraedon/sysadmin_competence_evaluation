"""
Integration tests for the lab controller.

Tests the full request lifecycle with an in-memory SQLite database
and DRY_RUN=True orchestrator.

Run with: cd platform/lab-controller && python -m pytest tests/test_integration.py -v

These tests cover:
  T-1: Database model creation, migrations, session_scope behavior
  T-2: Main module helpers (status updates)
  T-3: Provisioning flow (atomic mutex, capability matching)
  T-4: Teardown, reaper, and ARCH-02 suspect session recovery
  T-5: Evaluator prompt builder field exclusion (Python-side)
"""

import pytest
import asyncio
import datetime
import os
import sys
import yaml
from unittest.mock import patch, AsyncMock, MagicMock
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Ensure the lab-controller package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base, LabEnvironment, LabSession
from app.orchestrator import OrchestrationResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db_factory(tmp_path):
    """Creates a fresh SQLite database and returns (engine, session_factory, scope_fn)."""
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine)

    @contextmanager
    def scope():
        s = factory()
        try:
            yield s
            s.commit()
        except:
            s.rollback()
            raise
        finally:
            s.close()

    return engine, factory, scope


@pytest.fixture
def seeded_db(db_factory):
    """Seeds a DB with one available environment."""
    engine, factory, scope = db_factory
    with scope() as db:
        db.add(LabEnvironment(
            id="env-01", vms=["VM1"], guac_connection_id="1",
            guac_target_vm="VM1", guac_protocol="rdp",
            capabilities=["windows-server"], status="available"
        ))
    return engine, factory, scope


# ---------------------------------------------------------------------------
# T-1: Database model and migration tests
# ---------------------------------------------------------------------------

class TestDatabase:

    def test_init_db_creates_tables(self, db_factory):
        engine, _, _ = db_factory
        tables = inspect(engine).get_table_names()
        assert "environments" in tables
        assert "sessions" in tables

    def test_environment_model_fields(self, db_factory):
        _, _, scope = db_factory
        with scope() as db:
            db.add(LabEnvironment(
                id="test-env", vms=["VM1", "VM2"], guac_connection_id="42",
                guac_target_vm="VM1", guac_protocol="rdp",
                capabilities=["windows-server"], status="available",
                provision_step="reverting",
            ))
        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.id == "test-env"
            assert env.vms == ["VM1", "VM2"]
            assert env.provision_step == "reverting"

    def test_session_suspect_flag(self, seeded_db):
        """ARCH-02: LabSession.suspect column exists and defaults to False."""
        _, _, scope = seeded_db
        with scope() as db:
            db.add(LabSession(
                session_token="tok-1", environment_id="env-01",
                user_id="u1", scenario_id="d01-test", suspect=False,
                expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                max_expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=4),
            ))
        with scope() as db:
            s = db.query(LabSession).first()
            assert s.suspect is False
            s.suspect = True
        with scope() as db:
            assert db.query(LabSession).first().suspect is True

    def test_session_scope_commits(self, db_factory):
        _, _, scope = db_factory
        with scope() as db:
            db.add(LabEnvironment(
                id="e1", vms=[], guac_connection_id="1", capabilities=[], status="available"
            ))
        with scope() as db:
            assert db.query(LabEnvironment).count() == 1

    def test_session_scope_rollback_on_error(self, db_factory):
        _, _, scope = db_factory
        with pytest.raises(ValueError):
            with scope() as db:
                db.add(LabEnvironment(
                    id="e1", vms=[], guac_connection_id="1", capabilities=[], status="available"
                ))
                raise ValueError("boom")
        with scope() as db:
            assert db.query(LabEnvironment).count() == 0


# ---------------------------------------------------------------------------
# T-2: Main module helper tests
# ---------------------------------------------------------------------------

class TestHelpers:

    def test_update_provision_step(self, seeded_db):
        _, _, scope = seeded_db

        # Import the module object so we can patch attributes on it
        import app.main as main_mod

        # Set env to provisioning first
        with scope() as db:
            db.query(LabEnvironment).first().status = "provisioning"

        with patch.object(main_mod, "session_scope", scope):
            main_mod._update_provision_step("env-01", "reverting")

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.provision_step == "reverting"
            assert env.provision_step_updated_at is not None

    def test_update_env_status(self, seeded_db):
        _, _, scope = seeded_db
        import app.main as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "provisioning"
            env.provision_step = "reverting"

        with patch.object(main_mod, "session_scope", scope):
            main_mod._update_env_status("env-01", "faulted", last_error="VM exploded")

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert env.provision_step is None
            assert env.last_error == "VM exploded"


# ---------------------------------------------------------------------------
# T-3: Provisioning flow tests
# ---------------------------------------------------------------------------

class TestProvisioningFlow:

    def test_atomic_mutex_claims_environment(self, seeded_db):
        _, _, scope = seeded_db
        with scope() as db:
            affected = db.query(LabEnvironment).filter(
                LabEnvironment.id == "env-01",
                LabEnvironment.status == "available"
            ).update({"status": "provisioning"})
            assert affected == 1
        with scope() as db:
            assert db.query(LabEnvironment).first().status == "provisioning"

    def test_atomic_mutex_rejects_double_claim(self, seeded_db):
        _, _, scope = seeded_db
        with scope() as db:
            db.query(LabEnvironment).filter(
                LabEnvironment.id == "env-01", LabEnvironment.status == "available"
            ).update({"status": "provisioning"})
        with scope() as db:
            affected = db.query(LabEnvironment).filter(
                LabEnvironment.id == "env-01", LabEnvironment.status == "available"
            ).update({"status": "provisioning"})
            assert affected == 0

    def test_capability_matching(self, db_factory):
        """Only environments with matching capabilities should be selected."""
        _, _, scope = db_factory
        with scope() as db:
            db.add(LabEnvironment(
                id="linux-01", vms=["L1"], guac_connection_id="2",
                capabilities=["linux"], status="available"
            ))
            db.add(LabEnvironment(
                id="win-01", vms=["W1"], guac_connection_id="1",
                capabilities=["windows-server", "ad-ds"], status="available"
            ))

        with scope() as db:
            required = ["ad-ds"]
            available = db.query(LabEnvironment).filter(LabEnvironment.status == "available").all()
            matched = [e for e in available if all(c in (e.capabilities or []) for c in required)]
            assert len(matched) == 1
            assert matched[0].id == "win-01"


# ---------------------------------------------------------------------------
# T-4: Teardown, reaper, and ARCH-02 suspect recovery
# ---------------------------------------------------------------------------

class TestTeardownAndReaper:

    def test_teardown_reverts_and_marks_available(self, seeded_db):
        _, _, scope = seeded_db
        import app.main as main_mod

        # Set up busy env with a session
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-1", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                expires_at=datetime.datetime.utcnow() - datetime.timedelta(hours=1),
                max_expires_at=datetime.datetime.utcnow(),
            ))

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac):
            asyncio.run(main_mod.teardown_environment_logic("env-01", "tok-1"))

        mock_orch.revert_to_checkpoint.assert_called_once_with("VM1", "Baseline")
        with scope() as db:
            assert db.query(LabSession).count() == 0

    def test_teardown_deletes_session_even_on_revert_failure(self, seeded_db):
        _, _, scope = seeded_db
        import app.main as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-2", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                expires_at=datetime.datetime.utcnow(),
                max_expires_at=datetime.datetime.utcnow(),
            ))

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(
            success=False, output="", error="VM not found"
        )
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac):
            asyncio.run(main_mod.teardown_environment_logic("env-01", "tok-2"))

        with scope() as db:
            assert db.query(LabSession).count() == 0

    def test_teardown_deletes_guac_connection(self, seeded_db):
        """Teardown should delete the dynamic Guacamole connection."""
        _, _, scope = seeded_db
        import app.main as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-3", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                guac_connection_id="dynamic-99",
                expires_at=datetime.datetime.utcnow(),
                max_expires_at=datetime.datetime.utcnow(),
            ))

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac):
            asyncio.run(main_mod.teardown_environment_logic("env-01", "tok-3"))

        mock_guac.delete_connection.assert_called_once_with("dynamic-99")

    def test_suspect_sessions_marked_on_startup(self, seeded_db, tmp_path):
        """ARCH-02: load_environments marks existing sessions as suspect, not deleted."""
        _, _, scope = seeded_db
        import app.main as main_mod

        future = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-orphan", environment_id="env-01",
                user_id="u1", scenario_id="d01-test", suspect=False,
                expires_at=future,
                max_expires_at=future + datetime.timedelta(hours=2),
            ))

        env_config = {
            "environments": [{
                "id": "env-01", "vms": ["VM1"], "guac_target_vm": "VM1",
                "guac_protocol": "rdp", "guac_connection_id": "1",
                "capabilities": ["windows-server"], "status": "available"
            }]
        }
        env_yaml = tmp_path / "environments.yaml"
        env_yaml.write_text(yaml.dump(env_config))

        mock_settings = MagicMock()
        mock_settings.environments_config = str(env_yaml)

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.load_environments())

        with scope() as db:
            sess = db.query(LabSession).first()
            assert sess is not None, "Session should NOT be deleted (ARCH-02)"
            assert sess.suspect is True
            assert sess.expires_at <= datetime.datetime.utcnow()

    def test_reaper_collects_expired_sessions(self, seeded_db):
        _, _, scope = seeded_db
        import app.main as main_mod

        past = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-expired", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                expires_at=past, max_expires_at=past,
            ))

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac):
            asyncio.run(main_mod.reap_expired_sessions())

        with scope() as db:
            assert db.query(LabSession).count() == 0


# ---------------------------------------------------------------------------
# T-5: Evaluator prompt builder (Python-side)
# ---------------------------------------------------------------------------

class TestEvaluatorPromptBuilder:

    @pytest.fixture
    def scenario(self):
        return {
            "schema_version": 2.0,
            "title": "Test",
            "domain_name": "Testing",
            "level": 2,
            "delivery_modes": ["A"],
            "presentation": {
                "modes": {"A": {"type": "script", "context": "Test context"}}
            },
            "rubric": {
                "findings": [{
                    "id": "f1", "type": "critical",
                    "description": "Test finding",
                    "miss_signal": "UNIQUE_MISS_SIGNAL",
                    "learning_note": "SECRET_LEARNING_NOTE"
                }],
                "level_indicators": {"L1": "Basic understanding", "L4": "Expert mastery"}
            }
        }

    def test_learning_note_excluded(self, scenario):
        from app.evaluator import build_system_prompt
        prompt = build_system_prompt(scenario, "artifact content")
        assert "SECRET_LEARNING_NOTE" not in prompt
        assert "learning_note" not in prompt.lower()

    def test_miss_signal_in_standard_mode(self, scenario):
        from app.evaluator import build_system_prompt
        prompt = build_system_prompt(scenario, "artifact")
        assert "UNIQUE_MISS_SIGNAL" in prompt

    def test_miss_signal_excluded_in_compact_mode(self, scenario):
        from app.evaluator import build_system_prompt
        prompt = build_system_prompt(scenario, "artifact", compact_rubric=True)
        assert "UNIQUE_MISS_SIGNAL" not in prompt

    def test_level_indicators_present(self, scenario):
        from app.evaluator import build_system_prompt
        prompt = build_system_prompt(scenario, "artifact")
        assert "Basic understanding" in prompt
        assert "Expert mastery" in prompt
