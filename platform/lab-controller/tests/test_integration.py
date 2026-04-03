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
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from contextlib import contextmanager

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Ensure the lab-controller package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base, LabEnvironment, LabSession, LabHeartbeat
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
                expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1),
                max_expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=4),
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
        import app.services.lab_service as main_mod

        # Set env to provisioning first
        with scope() as db:
            db.query(LabEnvironment).first().status = "provisioning"

        with patch.object(main_mod, "session_scope", scope):
            main_mod.update_provision_step("env-01", "reverting")

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.provision_step == "reverting"
            assert env.provision_step_updated_at is not None

    def test_update_env_status(self, seeded_db):
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "provisioning"
            env.provision_step = "reverting"

        with patch.object(main_mod, "session_scope", scope):
            main_mod.update_env_status("env-01", "faulted", last_error="VM exploded")

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
        import app.services.lab_service as main_mod

        # Set up busy env with a session
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-1", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                expires_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
                max_expires_at=datetime.datetime.now(datetime.UTC),
            ))

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac):
            asyncio.run(main_mod.teardown_environment_logic("env-01", "tok-1"))

        mock_orch.revert_to_checkpoint.assert_called_once_with("VM1", "Baseline Checkpoint")
        with scope() as db:
            assert db.query(LabSession).count() == 0

    def test_teardown_deletes_session_even_on_revert_failure(self, seeded_db):
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-2", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                expires_at=datetime.datetime.now(datetime.UTC),
                max_expires_at=datetime.datetime.now(datetime.UTC),
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
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-3", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                guac_connection_id="dynamic-99",
                expires_at=datetime.datetime.now(datetime.UTC),
                max_expires_at=datetime.datetime.now(datetime.UTC),
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
        import app.services.lab_service as main_mod

        future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)
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
            # ARCH-02 fix (S29): expires_at is NOT forced to now() — busy sessions
            # must survive rolling deploys. Only the suspect flag is set.
            assert sess.expires_at > datetime.datetime.now(datetime.UTC)

    def test_reaper_collects_expired_sessions(self, seeded_db):
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=5)
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

    def test_reaper_logs_heartbeat(self, seeded_db):
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with patch.object(main_mod, "session_scope", scope):
            main_mod.reap_expired_sessions_wrapper()

        with scope() as db:
            hb = db.query(LabHeartbeat).filter(LabHeartbeat.job_name == "reap_expired_sessions").first()
            assert hb is not None
            assert hb.last_status == "success"

    def test_reconciler_logs_heartbeat(self, seeded_db):
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_orch = AsyncMock()
        mock_orch.get_vm_state.return_value = OrchestrationResult(success=True, output="Off")
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch):
            main_mod.reconcile_environments_wrapper()

        with scope() as db:
            hb = db.query(LabHeartbeat).filter(LabHeartbeat.job_name == "reconcile_environments").first()
            assert hb is not None
            assert hb.last_status == "success"


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


# ---------------------------------------------------------------------------
# T-6: Faulted environment detection and admin reset
# ---------------------------------------------------------------------------

class TestFaultedEnvironmentRecovery:
    """
    T-6: Faulted environment detection and admin reset.

    Root cause of "No capable lab environments currently available":
    Environments that enter 'faulted' status have no automatic recovery path.
    load_environments() explicitly preserves 'faulted' across pod restarts
    (intentionally — don't re-provision a known-bad VM), but there was no
    admin endpoint to clear it. Any provisioning failure permanently removes
    an environment from the pool until the DB is manually edited.

    These tests:
    1. Detect the problem (faulted → excluded from available pool)
    2. Verify the intentional design (faulted persists on restart)
    3. Verify the fix (admin reset clears fault and restores availability)
    """

    def test_faulted_env_excluded_from_available_query(self, seeded_db):
        """A faulted environment must not appear in the provisioning pool."""
        _, _, scope = seeded_db
        with scope() as db:
            db.query(LabEnvironment).filter(LabEnvironment.id == "env-01").update(
                {"status": "faulted"}
            )
        with scope() as db:
            available = db.query(LabEnvironment).filter(
                LabEnvironment.status == "available"
            ).all()
            assert len(available) == 0, "A faulted environment must not be provisioned"

    def test_faulted_status_persists_across_load_environments(self, seeded_db, tmp_path):
        """load_environments must NOT silently reset faulted environments on restart.

        Preserving 'faulted' is intentional — it prevents re-use of a known-bad
        VM — but it requires an explicit admin reset path to recover.
        This test documents the behaviour as a contract.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            db.query(LabEnvironment).filter(LabEnvironment.id == "env-01").update(
                {"status": "faulted", "last_error": "prior failure"}
            )

        env_config = {"environments": [{
            "id": "env-01", "vms": ["VM1"], "guac_target_vm": "VM1",
            "guac_protocol": "rdp", "guac_connection_id": "1",
            "capabilities": ["windows-server"], "status": "available"
        }]}
        env_yaml = tmp_path / "environments.yaml"
        env_yaml.write_text(yaml.dump(env_config))
        mock_settings = MagicMock()
        mock_settings.environments_config = str(env_yaml)

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.load_environments())

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted", (
                "load_environments should NOT reset faulted status — "
                "operator must use admin reset to recover intentionally"
            )

    def test_admin_reset_restores_faulted_to_available(self, seeded_db):
        """_reset_environment clears the fault and returns the previous status."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.last_error = "Checkpoint revert failed for VM1: access denied"
            env.provision_step = "reverting"

        with patch.object(main_mod, "session_scope", scope):
            previous = main_mod.reset_environment("env-01")

        assert previous == "faulted"
        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "available"
            assert env.last_error is None
            assert env.provision_step is None

    def test_admin_reset_rejects_active_environments(self, seeded_db):
        """Cannot reset an environment that is actively provisioning or in use.

        Resetting while active would orphan the running VM in an unknown state.
        """
        from fastapi import HTTPException
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        for active_status in ("provisioning", "busy", "teardown"):
            with scope() as db:
                db.query(LabEnvironment).filter(LabEnvironment.id == "env-01").update(
                    {"status": active_status}
                )
            with patch.object(main_mod, "session_scope", scope):
                with pytest.raises(HTTPException) as exc_info:
                    main_mod.reset_environment("env-01")
                assert exc_info.value.status_code == 409, \
                    f"Expected 409 for status={active_status!r}, got {exc_info.value.status_code}"

    def test_admin_reset_not_found_raises_404(self, db_factory):
        """_reset_environment raises 404 for an unknown environment ID."""
        from fastapi import HTTPException
        _, _, scope = db_factory
        import app.services.lab_service as main_mod

        with patch.object(main_mod, "session_scope", scope):
            with pytest.raises(HTTPException) as exc_info:
                main_mod.reset_environment("nonexistent-env")
            assert exc_info.value.status_code == 404

    def test_reset_all_faulted_restores_entire_pool(self, db_factory):
        """_reset_all_faulted resets every faulted environment in one call."""
        _, _, scope = db_factory
        with scope() as db:
            for env_id in ("env-a", "env-b", "env-c"):
                db.add(LabEnvironment(
                    id=env_id, vms=["VM1"], guac_connection_id="1",
                    capabilities=["windows-server"], status="faulted",
                    last_error="prior failure"
                ))
            # Add a non-faulted env to confirm it is untouched
            db.add(LabEnvironment(
                id="env-busy", vms=["VM2"], guac_connection_id="2",
                capabilities=["windows-server"], status="busy"
            ))

        import app.services.lab_service as main_mod
        with patch.object(main_mod, "session_scope", scope):
            reset_ids = main_mod.reset_all_faulted()

        assert set(reset_ids) == {"env-a", "env-b", "env-c"}
        with scope() as db:
            still_faulted = db.query(LabEnvironment).filter(
                LabEnvironment.status == "faulted"
            ).count()
            assert still_faulted == 0
            # Non-faulted env untouched
            busy_env = db.query(LabEnvironment).filter(LabEnvironment.id == "env-busy").first()
            assert busy_env.status == "busy"

    def test_reset_all_faulted_returns_empty_when_none_faulted(self, seeded_db):
        """_reset_all_faulted is a no-op (returns []) when no environments are faulted."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with patch.object(main_mod, "session_scope", scope):
            reset_ids = main_mod.reset_all_faulted()

        assert reset_ids == []

    def test_503_detail_identifies_faulted_environments(self, db_factory):
        """When all environments are faulted, the available query is empty.

        This test verifies the DB state that produces the 503 and confirms
        the admin reset path restores the environment to the available pool.
        """
        _, _, scope = db_factory
        import app.services.lab_service as main_mod

        with scope() as db:
            db.add(LabEnvironment(
                id="env-01", vms=["VM1"], guac_connection_id="1",
                capabilities=["windows-server"], status="faulted",
                last_error="WinRM timeout after 300s"
            ))

        # Confirm: nothing available
        with scope() as db:
            available = db.query(LabEnvironment).filter(
                LabEnvironment.status == "available"
            ).all()
            assert len(available) == 0

        # Fix: admin reset
        with patch.object(main_mod, "session_scope", scope):
            main_mod.reset_environment("env-01")

        # Confirm: now available
        with scope() as db:
            available = db.query(LabEnvironment).filter(
                LabEnvironment.status == "available"
            ).all()
            assert len(available) == 1

    def test_capability_mismatch_with_available_envs(self, db_factory):
        """When envs are available but lack required capabilities, none are selected.

        This is distinct from 'all faulted' — envs ARE available, just wrong type.
        The 503 detail should reflect the mismatch, not a fault.
        """
        _, _, scope = db_factory
        with scope() as db:
            db.add(LabEnvironment(
                id="linux-01", vms=["L1"], guac_connection_id="2",
                capabilities=["linux"], status="available"
            ))

        with scope() as db:
            available = db.query(LabEnvironment).filter(
                LabEnvironment.status == "available"
            ).all()
            required = ["windows-server"]
            matched = [
                e for e in available
                if all(c in (e.capabilities or []) for c in required)
            ]
            # Available envs exist, but none match
            assert len(available) == 1
            assert len(matched) == 0


# ---------------------------------------------------------------------------
# T-7: Reconciler — auto-recovery and orphan VM detection
# ---------------------------------------------------------------------------

class TestReconciler:
    """
    T-7: Periodic reconciler behaviour.

    The reconciler runs every RECONCILE_INTERVAL_MINUTES and does two things:
    1. Auto-retry faulted environments (up to fault_max_auto_retries times,
       with a delay of fault_auto_retry_delay_minutes between attempts).
    2. Detect orphan VMs — VMs that are Running while the environment is
       'available' (no active session) — and revert them to Baseline.
    """

    # ------------------------------------------------------------------ #
    # faulted_at stamping                                                 #
    # ------------------------------------------------------------------ #

    def test_faulted_at_stamped_when_env_first_faults(self, seeded_db):
        """_update_env_status('faulted') records faulted_at on first fault."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with patch.object(main_mod, "session_scope", scope):
            main_mod.update_env_status("env-01", "faulted", last_error="disk full")

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert env.faulted_at is not None

    def test_faulted_at_not_overwritten_on_second_fault(self, seeded_db):
        """Subsequent _update_env_status('faulted') calls do not clobber faulted_at.

        This preserves the original fault time so the retry delay is calculated
        from when the environment FIRST faulted, not from the last status write.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        first_fault = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1)
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = first_fault

        with patch.object(main_mod, "session_scope", scope):
            main_mod.update_env_status("env-01", "faulted", last_error="still broken")

        with scope() as db:
            env = db.query(LabEnvironment).first()
            # faulted_at must not have moved forward
            assert env.faulted_at <= first_fault + datetime.timedelta(seconds=1)

    def test_faulted_at_cleared_when_env_recovers(self, seeded_db):
        """_update_env_status('available') clears faulted_at and fault_retry_count."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = datetime.datetime.now(datetime.UTC)
            env.fault_retry_count = 2

        with patch.object(main_mod, "session_scope", scope):
            main_mod.update_env_status("env-01", "available")

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.faulted_at is None
            assert env.fault_retry_count == 0

    # ------------------------------------------------------------------ #
    # Retry eligibility                                                   #
    # ------------------------------------------------------------------ #

    def test_reconciler_skips_env_faulted_too_recently(self, seeded_db, tmp_path):
        """Env faulted seconds ago must not be retried — delay has not elapsed."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = datetime.datetime.now(datetime.UTC)  # just now
            env.fault_retry_count = 0

        mock_orch = AsyncMock()
        mock_guac = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        mock_orch.revert_to_checkpoint.assert_not_called()

    def test_reconciler_retries_env_past_delay(self, seeded_db):
        """Env faulted more than delay minutes ago IS eligible for auto-retry."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        old_fault_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=20)
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = old_fault_time
            env.fault_retry_count = 0

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_guac = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        mock_orch.revert_to_checkpoint.assert_called_once_with("VM1", "Baseline Checkpoint")
        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "available"

    def test_reconciler_skips_env_over_max_retries(self, seeded_db):
        """Env that has already hit fault_max_auto_retries is left for a human."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        old_fault_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2)
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = old_fault_time
            env.fault_retry_count = 2  # == fault_max_auto_retries

        mock_orch = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        mock_orch.revert_to_checkpoint.assert_not_called()

    # ------------------------------------------------------------------ #
    # Auto-recovery outcomes                                              #
    # ------------------------------------------------------------------ #

    def test_auto_recovery_success_resets_to_available(self, seeded_db):
        """Successful revert resets env to 'available' and clears all fault state."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15)
            env.fault_retry_count = 1
            env.last_error = "prior failure"

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_settings = MagicMock()
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.attempt_auto_recovery("env-01", ["VM1"]))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "available"
            assert env.last_error is None
            assert env.faulted_at is None
            assert env.fault_retry_count == 0

    def test_auto_recovery_failure_increments_retry_count(self, seeded_db):
        """Failed revert increments fault_retry_count and resets faulted_at timer."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "faulted"
            env.faulted_at = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15)
            env.fault_retry_count = 0

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(
            success=False, output="", error="WinRM timeout"
        )
        mock_settings = MagicMock()
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.attempt_auto_recovery("env-01", ["VM1"]))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert env.fault_retry_count == 1
            assert env.last_error is not None

    def test_auto_recovery_attempts_all_vms_even_if_one_fails(self, db_factory):
        """If the first VM revert fails, subsequent VMs are still attempted."""
        _, _, scope = db_factory
        with scope() as db:
            db.add(LabEnvironment(
                id="env-multi", vms=["VM1", "VM2", "VM3"], guac_connection_id="1",
                capabilities=["windows-domain", "ad-ds"], status="faulted",
                faulted_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=1),
                fault_retry_count=0
            ))

        import app.services.lab_service as main_mod
        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.side_effect = [
            OrchestrationResult(success=False, output="", error="access denied"),  # VM1 fails
            OrchestrationResult(success=True, output="ok"),                        # VM2 ok
            OrchestrationResult(success=True, output="ok"),                        # VM3 ok
        ]
        mock_settings = MagicMock()
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.attempt_auto_recovery("env-multi", ["VM1", "VM2", "VM3"]))

        assert mock_orch.revert_to_checkpoint.call_count == 3

    # ------------------------------------------------------------------ #
    # Orphan VM detection                                                 #
    # ------------------------------------------------------------------ #

    def test_orphan_vm_triggers_revert(self, seeded_db):
        """A Running VM in an 'available' environment is reverted to Baseline."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_orch = AsyncMock()
        mock_orch.get_vm_state.return_value = OrchestrationResult(success=True, output="Running")
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_settings = MagicMock()
        mock_settings.dry_run = False  # orphan detection requires non-dry-run
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        mock_orch.get_vm_state.assert_called_once_with("VM1")
        mock_orch.revert_to_checkpoint.assert_called_once_with("VM1", "Baseline Checkpoint")

    def test_off_vm_not_touched(self, seeded_db):
        """A VM that is already Off requires no remediation."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_orch = AsyncMock()
        mock_orch.get_vm_state.return_value = OrchestrationResult(success=True, output="Off")
        mock_settings = MagicMock()
        mock_settings.dry_run = False
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        mock_orch.revert_to_checkpoint.assert_not_called()

    def test_orphan_vm_revert_failure_marks_faulted(self, seeded_db):
        """If orphan VM revert fails, the environment is marked faulted."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_orch = AsyncMock()
        mock_orch.get_vm_state.return_value = OrchestrationResult(success=True, output="Running")
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(
            success=False, output="", error="VM locked"
        )
        mock_settings = MagicMock()
        mock_settings.dry_run = False
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert "VM locked" in env.last_error

    def test_orphan_detection_skipped_in_dry_run(self, seeded_db):
        """In dry_run mode, orphan VM detection is skipped entirely."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_orch = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.dry_run = True
        mock_settings.fault_auto_retry_delay_minutes = 10
        mock_settings.fault_max_auto_retries = 2
        mock_settings.baseline_checkpoint_name = "Baseline Checkpoint"

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.reconcile_environments())

        mock_orch.get_vm_state.assert_not_called()


# ---------------------------------------------------------------------------
# T-8: Shared-VM topology validation (ARCH-26)
# ---------------------------------------------------------------------------

class TestSharedVMValidation:
    """Tests for ARCH-26: startup validation of shared-VM topology."""

    def test_shared_vm_logs_warning(self, db_factory, tmp_path, caplog):
        """When two environments share a VM, load_environments logs a warning."""
        _, _, scope = db_factory
        import app.services.lab_service as main_mod

        env_config = {
            "environments": [
                {"id": "env-a", "vms": ["SharedVM", "VM-A"], "guac_target_vm": "SharedVM",
                 "guac_protocol": "rdp", "guac_connection_id": "1",
                 "capabilities": ["windows-server"], "status": "available"},
                {"id": "env-b", "vms": ["SharedVM", "VM-B"], "guac_target_vm": "SharedVM",
                 "guac_protocol": "rdp", "guac_connection_id": "2",
                 "capabilities": ["windows-server", "ad-ds"], "status": "available"},
            ]
        }
        env_yaml = tmp_path / "environments.yaml"
        env_yaml.write_text(yaml.dump(env_config))

        mock_settings = MagicMock()
        mock_settings.environments_config = str(env_yaml)

        import logging
        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "settings", mock_settings), \
             caplog.at_level(logging.WARNING):
            asyncio.run(main_mod.load_environments())

        assert any("SharedVM" in r.message and "ARCH-26" in r.message for r in caplog.records), \
            "Should log ARCH-26 warning about shared VM"

    def test_no_warning_when_vms_unique(self, db_factory, tmp_path, caplog):
        """No warning logged when environments have distinct VMs."""
        _, _, scope = db_factory
        import app.services.lab_service as main_mod

        env_config = {
            "environments": [
                {"id": "env-a", "vms": ["VM-A"], "guac_target_vm": "VM-A",
                 "guac_protocol": "rdp", "guac_connection_id": "1",
                 "capabilities": ["windows-server"], "status": "available"},
                {"id": "env-b", "vms": ["VM-B"], "guac_target_vm": "VM-B",
                 "guac_protocol": "ssh", "guac_connection_id": "2",
                 "capabilities": ["linux"], "status": "available"},
            ]
        }
        env_yaml = tmp_path / "environments.yaml"
        env_yaml.write_text(yaml.dump(env_config))

        mock_settings = MagicMock()
        mock_settings.environments_config = str(env_yaml)

        import logging
        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "settings", mock_settings), \
             caplog.at_level(logging.WARNING):
            asyncio.run(main_mod.load_environments())

        assert not any("ARCH-26" in r.message for r in caplog.records), \
            "Should NOT log ARCH-26 warning when VMs are unique"


# ---------------------------------------------------------------------------
# T-9: Provisioning flow execution (TEST-02)
# ---------------------------------------------------------------------------

class TestProvisioningFlowExecution:
    """
    T-9: run_provisioning_flow / run_provisioning_with_watchdog execution.

    The provisioning flow was the source of the most S26/S29 production bugs, all
    of which were found manually. These tests cover the three highest-priority gaps
    from breadcrumbs/test-02-missing-high-value-tests.md, plus lifecycle invariants
    for teardown resilience and the reaper.

    All tests use the seeded_db fixture (env-01, VM1, rdp) and a default
    'provisioning_mock_orch' fixture that returns success for every step,
    so individual tests only need to override the step they're exercising.
    """

    @pytest.fixture
    def provisioning_mock_orch(self):
        """Mock orchestrator with all provisioning operations succeeding by default."""
        mock = AsyncMock()
        mock.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock.start_vm.return_value = OrchestrationResult(success=True, output="ok")
        mock.wait_for_guest_readiness.return_value = True
        mock.get_vm_ip.return_value = OrchestrationResult(success=True, output="192.168.1.100")
        return mock

    @pytest.fixture
    def mock_settings(self):
        s = MagicMock()
        s.baseline_checkpoint_name = "Baseline Checkpoint"
        s.hyperv_guest_username = "administrator"
        s.hyperv_guest_password = "testpass"
        s.provisioning_timeout_seconds = 300
        return s

    # ------------------------------------------------------------------ #
    # Priority 1: Error propagation                                        #
    # ------------------------------------------------------------------ #

    def test_provisioning_faults_on_revert_failure(self, seeded_db, provisioning_mock_orch, mock_settings):
        """Revert failure must fault the environment, not leave it in 'provisioning'.

        Bug this catches: S26 bug #2 — the guard was missing and provisioning
        continued silently after revert_to_checkpoint returned success=False.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        provisioning_mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(
            success=False, output="", error="Checkpoint not found"
        )
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", provisioning_mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_flow(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-test"
            ))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert "Checkpoint not found" in env.last_error

    def test_provisioning_faults_on_start_vm_failure(self, seeded_db, provisioning_mock_orch, mock_settings):
        """start_vm failure must fault the environment."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        provisioning_mock_orch.start_vm.return_value = OrchestrationResult(
            success=False, output="", error="VM failed to start"
        )
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", provisioning_mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_flow(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-test"
            ))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert "VM failed to start" in env.last_error

    def test_provisioning_faults_on_readiness_timeout(self, seeded_db, provisioning_mock_orch, mock_settings):
        """wait_for_guest_readiness returning False must fault the environment."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        provisioning_mock_orch.wait_for_guest_readiness.return_value = False
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", provisioning_mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_flow(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-test"
            ))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert "readiness" in env.last_error.lower()

    def test_provisioning_success_marks_env_busy(self, seeded_db, provisioning_mock_orch, mock_settings):
        """Happy-path: all orchestration steps succeed → environment becomes 'busy'."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_guac = AsyncMock()
        mock_guac.create_connection.return_value = ("guac-id-1", None)
        mock_guac.create_session_user.return_value = ("sess-user", "sess-pass")

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", provisioning_mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_flow(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-test"
            ))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "busy"

    # ------------------------------------------------------------------ #
    # Priority 2: Guacamole domain\username splitting                     #
    # ------------------------------------------------------------------ #

    def test_domain_username_split_for_rdp(self, seeded_db, provisioning_mock_orch, mock_settings):
        """'domain\\\\username' in hyperv_guest_username is split into separate RDP params.

        Bug this catches: S29 bug #3 — the full 'ad.labdomain.dev\\\\claude' string
        was passed as username to Guacamole/FreeRDP, causing a login-failure loop
        because RDP rejects a domain-qualified username in the username field.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_settings.hyperv_guest_username = r"ad.labdomain.dev\claude"
        mock_guac = AsyncMock()
        mock_guac.create_connection.return_value = ("guac-id-1", None)
        mock_guac.create_session_user.return_value = ("sess-user", "sess-pass")

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", provisioning_mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_flow(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-test"
            ))

        mock_guac.create_connection.assert_called_once()
        params = mock_guac.create_connection.call_args.args[2]
        assert params["username"] == "claude", \
            f"Expected username 'claude', got {params['username']!r}"
        assert params["domain"] == "ad.labdomain.dev", \
            f"Expected domain 'ad.labdomain.dev', got {params.get('domain')!r}"

    def test_plain_username_has_no_domain_field(self, seeded_db, provisioning_mock_orch, mock_settings):
        """Username without backslash is passed as-is with no 'domain' param."""
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        mock_settings.hyperv_guest_username = "administrator"
        mock_guac = AsyncMock()
        mock_guac.create_connection.return_value = ("guac-id-1", None)
        mock_guac.create_session_user.return_value = ("sess-user", "sess-pass")

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", provisioning_mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_flow(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-test"
            ))

        mock_guac.create_connection.assert_called_once()
        params = mock_guac.create_connection.call_args.args[2]
        assert params["username"] == "administrator"
        assert "domain" not in params

    # ------------------------------------------------------------------ #
    # Priority 3: Watchdog triggers teardown on timeout                  #
    # ------------------------------------------------------------------ #

    def test_watchdog_triggers_teardown_on_timeout(self, seeded_db, mock_settings):
        """Provisioning timeout fires teardown and leaves the environment 'faulted'.

        Bug this catches: S26 bug #2 (pre-watchdog) — hung provisioning permanently
        locked an environment. The watchdog's job is to ensure that even if
        provisioning hangs, VMs are reverted and the environment is recoverable.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            db.add(LabSession(
                session_token="tok-watchdog", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2),
                max_expires_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=4),
            ))

        revert_call_count = 0

        async def slow_then_fast(vm, checkpoint):
            nonlocal revert_call_count
            revert_call_count += 1
            if revert_call_count == 1:
                await asyncio.sleep(100)  # Cancelled by the watchdog timeout
            return OrchestrationResult(success=True, output="ok")

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.side_effect = slow_then_fast
        mock_guac = AsyncMock()
        mock_settings.provisioning_timeout_seconds = 0.1  # 100 ms

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.run_provisioning_with_watchdog(
                "env-01", Path("/fake/scenario.yaml"), {}, "tok-watchdog"
            ))

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "faulted"
            assert "timed out" in (env.last_error or "").lower()
        # Teardown must have issued its own revert after the provisioning revert was cancelled
        assert revert_call_count >= 2, \
            "Watchdog should call teardown, which issues a second revert_to_checkpoint"

    # ------------------------------------------------------------------ #
    # Priority 4: load_environments preserves busy status               #
    # ------------------------------------------------------------------ #

    def test_busy_env_preserved_across_load_environments(self, seeded_db, tmp_path):
        """load_environments must not reset a 'busy' environment to 'available'.

        Bug this catches: S29 bug #7 — load_environments reset 'busy' envs on
        restart, which triggered the reconciler to revert actively-used VMs and
        disconnect the learner's session.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            db.query(LabEnvironment).first().status = "busy"

        env_config = {"environments": [{
            "id": "env-01", "vms": ["VM1"], "guac_target_vm": "VM1",
            "guac_protocol": "rdp", "guac_connection_id": "1",
            "capabilities": ["windows-server"], "status": "available"
        }]}
        env_yaml = tmp_path / "environments.yaml"
        env_yaml.write_text(yaml.dump(env_config))
        mock_settings = MagicMock()
        mock_settings.environments_config = str(env_yaml)

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.load_environments())

        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "busy", (
                "load_environments must not reset 'busy' status — "
                "the environment has an active session and a running VM"
            )

    # ------------------------------------------------------------------ #
    # Priority 6: Teardown resilience                                     #
    # ------------------------------------------------------------------ #

    def test_guac_failure_does_not_prevent_vm_revert(self, seeded_db, mock_settings):
        """Guacamole deletion failure must not abort VM revert during teardown.

        VMs being reverted is the critical operation (they're metered infrastructure);
        Guacamole connection cleanup is best-effort and wrapped in try/except.
        A refactor that accidentally makes a Guacamole failure abort teardown would
        leave VMs running indefinitely.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-teardown", environment_id="env-01",
                user_id="u1", scenario_id="d01-test",
                guac_connection_id="stale-conn-99",
                expires_at=datetime.datetime.now(datetime.UTC),
                max_expires_at=datetime.datetime.now(datetime.UTC),
            ))

        mock_orch = AsyncMock()
        mock_orch.revert_to_checkpoint.return_value = OrchestrationResult(success=True, output="ok")
        mock_guac = AsyncMock()
        mock_guac.delete_connection.side_effect = Exception("Guacamole connection not found")

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac), \
             patch.object(main_mod, "settings", mock_settings):
            asyncio.run(main_mod.teardown_environment_logic("env-01", "tok-teardown"))

        mock_orch.revert_to_checkpoint.assert_called_once()
        with scope() as db:
            env = db.query(LabEnvironment).first()
            assert env.status == "available"

    # ------------------------------------------------------------------ #
    # Priority 7: Reaper leaves suspect sessions with future expiry      #
    # ------------------------------------------------------------------ #

    def test_reaper_spares_suspect_session_with_future_expiry(self, seeded_db):
        """Suspect sessions that have not yet expired must survive the reaper.

        Bug this catches: S29 bug #6 — the reaper was killing sessions marked
        suspect at restart because a prior fix had set expires_at = now(), causing
        them to appear expired. The correct fix (stop touching expires_at) relies
        on this invariant: the reaper filters by expires_at only, not the suspect flag.
        """
        _, _, scope = seeded_db
        import app.services.lab_service as main_mod

        future = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=1)
        with scope() as db:
            env = db.query(LabEnvironment).first()
            env.status = "busy"
            db.add(LabSession(
                session_token="tok-suspect", environment_id="env-01",
                user_id="u1", scenario_id="d01-test", suspect=True,
                expires_at=future,
                max_expires_at=future + datetime.timedelta(hours=2),
            ))

        mock_orch = AsyncMock()
        mock_guac = AsyncMock()

        with patch.object(main_mod, "session_scope", scope), \
             patch.object(main_mod, "orchestrator", mock_orch), \
             patch.object(main_mod, "guac_client", mock_guac):
            asyncio.run(main_mod.reap_expired_sessions())

        with scope() as db:
            assert db.query(LabSession).count() == 1, \
                "Suspect session with future expiry must survive the reaper"
        mock_orch.revert_to_checkpoint.assert_not_called()
