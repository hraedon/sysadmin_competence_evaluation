import os
import yaml
import datetime
import logging
import asyncio
import uuid
from pathlib import Path
from typing import List, Optional, Tuple

from ..database import session_scope, LabEnvironment, LabSession, LabHeartbeat
from ..schemas import settings
from ..deps import orchestrator, guac_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Initialization & Lifecycle
# ---------------------------------------------------------------------------

async def load_environments():
    """Seed or update the database with environments from config."""
    if not os.path.exists(settings.environments_config):
        logger.warning(f"Environments config {settings.environments_config} not found.")
        return

    with open(settings.environments_config, 'r') as f:
        config = yaml.safe_load(f)

    with session_scope() as db:
        # ARCH-02: Mark survival sessions as suspect
        orphaned = db.query(LabSession).all()
        for sess in orphaned:
            sess.suspect = True
            sess.expires_at = datetime.datetime.now(datetime.UTC)
            logger.info(f"Marked session {sess.session_token} as suspect (restart recovery)")

        for env_data in config.get('environments', []):
            existing = db.query(LabEnvironment).filter(LabEnvironment.id == env_data['id']).first()
            target_status = env_data.get('status', "available")

            if not existing:
                env = LabEnvironment(
                    id=env_data['id'],
                    vms=env_data['vms'],
                    guac_connection_id=env_data['guac_connection_id'],
                    guac_target_vm=env_data.get('guac_target_vm'),
                    guac_protocol=env_data.get('guac_protocol'),
                    capabilities=env_data['capabilities'],
                    status=target_status
                )
                db.add(env)
            else:
                existing.vms = env_data['vms']
                existing.capabilities = env_data['capabilities']
                existing.guac_connection_id = env_data['guac_connection_id']
                existing.guac_target_vm = env_data.get('guac_target_vm')
                existing.guac_protocol = env_data.get('guac_protocol')
                if existing.status not in ["available", "faulted"]:
                    existing.status = target_status

# ---------------------------------------------------------------------------
# Background Jobs (Scheduler Wrappers)
# ---------------------------------------------------------------------------

def log_heartbeat(job_name: str, status: str, error: Optional[str] = None):
    with session_scope() as db:
        hb = db.query(LabHeartbeat).filter(LabHeartbeat.job_name == job_name).first()
        if not hb:
            hb = LabHeartbeat(job_name=job_name)
            db.add(hb)
        hb.last_run_at = datetime.datetime.now(datetime.UTC)
        hb.last_status = status
        hb.last_error = error

def reap_expired_sessions_wrapper():
    try:
        asyncio.run(reap_expired_sessions())
        log_heartbeat("reap_expired_sessions", "success")
    except Exception as e:
        logger.error(f"reap_expired_sessions_wrapper failed: {e}")
        log_heartbeat("reap_expired_sessions", "error", str(e))

def reconcile_environments_wrapper():
    try:
        asyncio.run(reconcile_environments())
        log_heartbeat("reconcile_environments", "success")
    except Exception as e:
        logger.error(f"reconcile_environments_wrapper failed: {e}")
        log_heartbeat("reconcile_environments", "error", str(e))

async def reap_expired_sessions():
    now = datetime.datetime.now(datetime.UTC)
    with session_scope() as db:
        expired = db.query(LabSession).filter(LabSession.expires_at < now).all()
        expired_pairs = [(s.environment_id, s.session_token) for s in expired]

    for env_id, token in expired_pairs:
        logger.info(f"Reaping expired session {token} for env {env_id}")
        await teardown_environment_logic(env_id, token)

async def reconcile_environments():
    now = datetime.datetime.now(datetime.UTC)
    retry_cutoff = now - datetime.timedelta(minutes=settings.fault_auto_retry_delay_minutes)

    with session_scope() as db:
        eligible = [
            (e.id, list(e.vms))
            for e in db.query(LabEnvironment).filter(
                LabEnvironment.status == "faulted",
                LabEnvironment.fault_retry_count < settings.fault_max_auto_retries,
            ).all()
            if e.faulted_at is None or e.faulted_at <= retry_cutoff
        ]

    for env_id, vm_list in eligible:
        logger.info(f"Reconciler: attempting auto-recovery for faulted env '{env_id}'")
        await attempt_auto_recovery(env_id, vm_list)

    if settings.dry_run: return

    with session_scope() as db:
        available_list = [(e.id, list(e.vms)) for e in db.query(LabEnvironment).filter(LabEnvironment.status == "available").all()]

    for env_id, vm_list in available_list:
        for vm in vm_list:
            state_res = await orchestrator.get_vm_state(vm)
            if state_res.success and state_res.output.strip().lower() != "off":
                logger.warning(f"Reconciler: orphan VM '{vm}' in '{env_id}' is running. Reverting.")
                revert_res = await orchestrator.revert_to_checkpoint(vm, settings.baseline_checkpoint_name)
                if not revert_res.success:
                    update_env_status(env_id, "faulted", last_error=f"Orphan VM revert failed: {revert_res.error}")

async def attempt_auto_recovery(env_id: str, vm_list: list):
    checkpoint = settings.baseline_checkpoint_name
    success = True
    last_error = None
    for vm in vm_list:
        res = await orchestrator.revert_to_checkpoint(vm, checkpoint)
        if not res.success:
            success = False
            last_error = f"Auto-recovery revert failed for '{vm}': {res.error}"

    if success:
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if env:
                env.status = "available"
                env.last_error = None
                env.provision_step = None
                env.faulted_at = None
                env.fault_retry_count = 0
        logger.info(f"Reconciler: auto-recovered env '{env_id}'")
    else:
        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            if env:
                env.fault_retry_count = (env.fault_retry_count or 0) + 1
                env.faulted_at = datetime.datetime.now(datetime.UTC)
                env.last_error = last_error

# ---------------------------------------------------------------------------
# Core Orchestration Logic
# ---------------------------------------------------------------------------

async def run_provisioning_with_watchdog(env_id: str, scenario_path: Path, mode_e: dict, session_token: str):
    try:
        await asyncio.wait_for(
            run_provisioning_flow(env_id, scenario_path, mode_e, session_token),
            timeout=settings.provisioning_timeout_seconds
        )
    except asyncio.TimeoutError:
        logger.error(f"Provisioning watchdog timeout ({settings.provisioning_timeout_seconds}s) for {env_id}")
        update_env_status(env_id, "faulted", last_error=f"Provisioning timed out after {settings.provisioning_timeout_seconds}s")

async def run_provisioning_flow(env_id: str, scenario_path: Path, mode_e: dict, session_token: str):
    try:
        checkpoint = mode_e.get('checkpoint', 'Baseline')
        config = mode_e.get('config', {})
        provisioning_actions = config.get('provisioning', [])

        with session_scope() as db:
            env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
            vm_targets = list(env.vms)
            guac_target_vm = env.guac_target_vm
            guac_protocol = env.guac_protocol

        update_provision_step(env_id, "reverting")
        for vm in vm_targets:
            res = await orchestrator.revert_to_checkpoint(vm, checkpoint)
            if not res.success: raise Exception(f"Revert failed for {vm}: {res.error}")

        update_provision_step(env_id, "starting")
        for vm in vm_targets:
            res = await orchestrator.start_vm(vm)
            if not res.success: raise Exception(f"Start failed for {vm}: {res.error}")

        update_provision_step(env_id, "waiting_ip")
        async def _on_conn(): update_provision_step(env_id, "testing_connectivity")
        for vm in vm_targets:
            if not await orchestrator.wait_for_guest_readiness(vm, on_connectivity_phase=_on_conn):
                raise Exception(f"Timeout waiting for {vm} readiness")

        update_provision_step(env_id, "creating_guac")
        if guac_target_vm and guac_protocol:
            ip_res = await orchestrator.get_vm_ip(guac_target_vm)
            if ip_res.success and ip_res.output:
                params = {"hostname": ip_res.output, "username": "labuser", "password": settings.hyperv_guest_password}
                if guac_protocol == "rdp":
                    params["ignore-cert"] = "true"
                    params["security"] = "any"

                guac_id, _ = await guac_client.create_connection(f"Session-{session_token[:8]}", guac_protocol, params)

                # SEC-07: Create a restricted session user instead of sharing admin token
                guac_username = None
                guac_password = None
                try:
                    guac_username, guac_password = await guac_client.create_session_user(session_token, guac_id)
                except Exception as e:
                    logger.warning(f"SEC-07: Failed to create session user, will fall back to admin token: {e}")

                with session_scope() as db:
                    sess = db.query(LabSession).filter(LabSession.session_token == session_token).first()
                    if sess:
                        sess.guac_connection_id = guac_id
                        sess.guac_session_username = guac_username
                        sess.guac_session_password = guac_password

        update_provision_step(env_id, "running_scripts")
        for action in provisioning_actions:
            target, act_type = action.get('target'), action.get('action')
            res = None
            if act_type == "run_script":
                res = await orchestrator.run_script_in_guest(target, str(scenario_path.parent / action.get('file')))
            elif act_type == "copy_file":
                res = await orchestrator.copy_file_to_guest(target, str(scenario_path.parent / action.get('source')), action.get('destination'))
            if res and not res.success: raise Exception(f"Action {act_type} failed on {target}: {res.error}")

        update_env_status(env_id, "busy")
    except Exception as e:
        logger.error(f"Provisioning failed for {env_id}: {str(e)}")
        update_env_status(env_id, "faulted", last_error=str(e))

async def teardown_environment_logic(env_id: str, session_token: str):
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if not env: return
        vm_list = list(env.vms)
        env.status = "teardown"

    guac_conn_id = None
    guac_session_user = None
    with session_scope() as db:
        session = db.query(LabSession).filter(LabSession.session_token == session_token).first()
        if session:
            guac_conn_id = session.guac_connection_id
            guac_session_user = session.guac_session_username

    # SEC-07: Delete session user before connection (user references the connection)
    if guac_session_user:
        try: await guac_client.delete_session_user(guac_session_user)
        except Exception as e: logger.error(f"Failed to delete Guacamole session user {guac_session_user}: {str(e)}")

    if guac_conn_id:
        try: await guac_client.delete_connection(guac_conn_id)
        except Exception as e: logger.error(f"Failed to delete Guacamole connection {guac_conn_id}: {str(e)}")

    try:
        success, last_error = True, None
        for vm in vm_list:
            res = await orchestrator.revert_to_checkpoint(vm, settings.baseline_checkpoint_name)
            if not res.success: success, last_error = False, f"Teardown failed on {vm}: {res.error}"
        update_env_status(env_id, "available" if success else "faulted", last_error=last_error)
    except Exception as e:
        logger.error(f"Teardown exception for {env_id}: {str(e)}")
        update_env_status(env_id, "faulted", last_error=str(e))
    finally:
        with session_scope() as db:
            db.query(LabSession).filter(LabSession.session_token == session_token).delete()

# ---------------------------------------------------------------------------
# Admin & Recovery
# ---------------------------------------------------------------------------

def reset_environment(env_id: str) -> str:
    """Reset a non-active environment to 'available' and clear its fault state."""
    from fastapi import HTTPException # Local import to avoid circular dependency
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if not env:
            raise HTTPException(status_code=404, detail=f"Environment '{env_id}' not found.")
        if env.status in ("provisioning", "busy", "teardown"):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot reset '{env_id}': currently '{env.status}'."
            )
        previous = env.status
        env.status = "available"
        env.last_error = None
        env.provision_step = None
        env.faulted_at = None
        env.fault_retry_count = 0
        return previous

def reset_all_faulted() -> List[str]:
    """Reset every faulted environment to 'available'."""
    with session_scope() as db:
        faulted = db.query(LabEnvironment).filter(LabEnvironment.status == "faulted").all()
        reset_ids = [e.id for e in faulted]
        for env in faulted:
            env.status = "available"
            env.last_error = None
            env.provision_step = None
            env.faulted_at = None
            env.fault_retry_count = 0
        return reset_ids

# ---------------------------------------------------------------------------
# Status Helpers
# ---------------------------------------------------------------------------

def update_provision_step(env_id: str, step: str):
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if env:
            env.provision_step = step
            env.provision_step_updated_at = datetime.datetime.now(datetime.UTC)

def update_env_status(env_id: str, status: str, provision_step=None, last_error=None):
    with session_scope() as db:
        env = db.query(LabEnvironment).filter(LabEnvironment.id == env_id).first()
        if env:
            env.status = status
            env.provision_step = provision_step
            env.provision_step_updated_at = None
            env.last_error = last_error
            if status == "faulted" and not env.faulted_at:
                env.faulted_at = datetime.datetime.now(datetime.UTC)
            elif status == "available":
                env.faulted_at = None
                env.fault_retry_count = 0
