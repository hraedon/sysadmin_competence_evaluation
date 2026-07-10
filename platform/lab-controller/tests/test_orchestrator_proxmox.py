"""
Tests for the Proxmox VE orchestrator.

Covers:
  - Dry-run behaviour for all operations
  - _resolve_vmid() with name mappings and numeric IDs
  - _wait_for_task() with mocked task status responses
  - _api_request() with mocked aiohttp responses
  - Error handling (HTTP errors, task failures, missing files)
  - IP parsing logic with sample network-get-interfaces response
  - VM state parsing
  - Guest script execution (file-write + exec + exec-status polling)
  - File copy to guest

Run with: cd platform/lab-controller && python -m pytest tests/test_orchestrator_proxmox.py -v
"""

import asyncio
import base64
import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.orchestrator_proxmox import ProxmoxOrchestrator
from app.orchestrator_base import OrchestrationResult


# ---------------------------------------------------------------------------
# Helpers: build mock aiohttp session / response objects
# ---------------------------------------------------------------------------

def make_mock_response(status_code, data):
    """Create a mock aiohttp response object."""
    response = AsyncMock()
    response.status = status_code
    response.json = AsyncMock(return_value={"data": data})
    response.text = AsyncMock(return_value=json.dumps({"data": data}))
    return response


def make_mock_ctx(response):
    """Create an async context manager that yields the given response."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=response)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


def make_mock_session(responses):
    """Create a mock aiohttp.ClientSession.

    Args:
        responses: a single mock ctx, or a list of mock ctxs for sequential calls.
    """
    session = MagicMock()
    session.closed = False
    if isinstance(responses, list):
        session.request = MagicMock(side_effect=responses)
    else:
        session.request = MagicMock(return_value=responses)
    return session


def make_orchestrator(dry_run=False, **kwargs):
    """Create a ProxmoxOrchestrator with sensible defaults for testing."""
    defaults = dict(
        api_url="https://pve.test:8006",
        api_token_id="user@pam!test-token",
        api_token_secret="secret-token-value",
        node="pve",
        verify_ssl=False,
        vm_name_to_id={"LabServer01": "100", "LabServer02": "101"},
        dry_run=dry_run,
    )
    defaults.update(kwargs)
    return ProxmoxOrchestrator(**defaults)


# ---------------------------------------------------------------------------
# Dry-run tests
# ---------------------------------------------------------------------------

class TestDryRun:
    """All operations in dry-run mode should succeed without making HTTP calls."""

    @pytest.fixture
    def orch(self):
        return make_orchestrator(dry_run=True)

    @pytest.mark.asyncio
    async def test_revert_to_checkpoint_dry_run(self, orch):
        res = await orch.revert_to_checkpoint("LabServer01", "baseline")
        assert res.success
        assert res.output == "Dry run success"

    @pytest.mark.asyncio
    async def test_start_vm_dry_run(self, orch):
        res = await orch.start_vm("LabServer01")
        assert res.success
        assert res.output == "Dry run success"

    @pytest.mark.asyncio
    async def test_stop_vm_dry_run(self, orch):
        res = await orch.stop_vm("LabServer01", force=True)
        assert res.success
        assert res.output == "Dry run success"

    @pytest.mark.asyncio
    async def test_stop_vm_graceful_dry_run(self, orch):
        res = await orch.stop_vm("LabServer01", force=False)
        assert res.success
        assert res.output == "Dry run success"

    @pytest.mark.asyncio
    async def test_get_vm_ip_dry_run(self, orch):
        res = await orch.get_vm_ip("LabServer01")
        assert res.success
        assert res.output == "192.168.100.15"

    @pytest.mark.asyncio
    async def test_test_guest_connectivity_dry_run(self, orch):
        res = await orch.test_guest_connectivity("LabServer01")
        assert res.success
        assert res.output == "OK"

    @pytest.mark.asyncio
    async def test_get_vm_state_dry_run(self, orch):
        res = await orch.get_vm_state("LabServer01")
        assert res.success
        assert res.output == "stopped"

    @pytest.mark.asyncio
    async def test_run_script_in_guest_dry_run(self, orch):
        res = await orch.run_script_in_guest("LabServer01", "/fake/script.sh")
        assert res.success
        parsed = json.loads(res.output)
        assert parsed["status"] == "correct"

    @pytest.mark.asyncio
    async def test_copy_file_to_guest_dry_run(self, orch):
        res = await orch.copy_file_to_guest("LabServer01", "/fake/src", "/tmp/dst")
        assert res.success
        assert res.output == "Dry run success"

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create_session(self, orch):
        await orch.revert_to_checkpoint("LabServer01", "baseline")
        assert orch._session is None

    @pytest.mark.asyncio
    async def test_dry_run_wait_for_task(self, orch):
        result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is True


# ---------------------------------------------------------------------------
# _resolve_vmid tests
# ---------------------------------------------------------------------------

class TestResolveVmid:

    def test_resolves_by_name_mapping(self):
        orch = make_orchestrator()
        assert orch._resolve_vmid("LabServer01") == "100"
        assert orch._resolve_vmid("LabServer02") == "101"

    def test_resolves_numeric_id_directly(self):
        orch = make_orchestrator()
        assert orch._resolve_vmid("200") == "200"
        assert orch._resolve_vmid("999") == "999"

    def test_resolves_numeric_id_with_empty_mapping(self):
        orch = make_orchestrator(vm_name_to_id=None)
        assert orch._resolve_vmid("100") == "100"

    def test_raises_on_unknown_name(self):
        orch = make_orchestrator()
        with pytest.raises(ValueError, match="Cannot resolve VM name 'UnknownVM'"):
            orch._resolve_vmid("UnknownVM")

    def test_raises_on_unknown_name_shows_mappings(self):
        orch = make_orchestrator()
        with pytest.raises(ValueError, match="LabServer01"):
            orch._resolve_vmid("UnknownVM")

    def test_name_mapping_takes_precedence_over_numeric(self):
        orch = make_orchestrator(vm_name_to_id={"100": "200"})
        assert orch._resolve_vmid("100") == "200"

    def test_resolves_non_string_vmid_from_mapping(self):
        orch = make_orchestrator(vm_name_to_id={"LabServer01": 100})
        assert orch._resolve_vmid("LabServer01") == "100"


# ---------------------------------------------------------------------------
# _api_request tests (mocked aiohttp)
# ---------------------------------------------------------------------------

class TestApiRequest:

    @pytest.mark.asyncio
    async def test_successful_get(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "running", "vmid": 100})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/nodes/pve/qemu/100/status/current")

        assert res.success
        data = json.loads(res.output)
        assert data["status"] == "running"
        assert data["vmid"] == 100

    @pytest.mark.asyncio
    async def test_successful_get_with_list_data(self):
        orch = make_orchestrator()
        response = make_mock_response(200, [{"name": "eth0"}, {"name": "lo"}])
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/nodes/pve/qemu/100/agent/network-get-interfaces")

        assert res.success
        data = json.loads(res.output)
        assert isinstance(data, list)
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_successful_post_returns_upid(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00001234:0000ABCD:..."
        response = make_mock_response(200, upid)
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("POST", "/api2/json/nodes/pve/qemu/100/status/start")

        assert res.success
        assert json.loads(res.output) == upid

    @pytest.mark.asyncio
    async def test_http_error_404(self):
        orch = make_orchestrator()
        response = make_mock_response(404, {"errors": "not found"})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/nodes/pve/qemu/999/status/current")

        assert not res.success
        assert "HTTP 404" in res.error

    @pytest.mark.asyncio
    async def test_http_error_500(self):
        orch = make_orchestrator()
        response = make_mock_response(500, {"errors": "internal error"})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/nodes/pve/qemu/100/status/current")

        assert not res.success
        assert "HTTP 500" in res.error

    @pytest.mark.asyncio
    async def test_http_error_403(self):
        orch = make_orchestrator()
        response = make_mock_response(403, {"errors": "permission denied"})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("POST", "/api2/json/nodes/pve/qemu/100/status/start")

        assert not res.success
        assert "HTTP 403" in res.error

    @pytest.mark.asyncio
    async def test_network_error(self):
        orch = make_orchestrator()
        session = MagicMock()
        session.closed = False
        session.request = MagicMock(side_effect=ConnectionError("Connection refused"))
        orch._session = session

        res = await orch._api_request("GET", "/api2/json/nodes/pve/qemu/100/status/current")

        assert not res.success
        assert "Connection refused" in res.error

    @pytest.mark.asyncio
    async def test_non_json_response(self):
        orch = make_orchestrator()
        response = AsyncMock()
        response.status = 502
        response.json = AsyncMock(side_effect=Exception("not JSON"))
        response.text = AsyncMock(return_value="<html>Bad Gateway</html>")
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/nodes/pve/qemu/100/status/current")

        assert not res.success
        assert "HTTP 502" in res.error
        assert "Non-JSON" in res.error

    @pytest.mark.asyncio
    async def test_data_envelope_unwrapped(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"key": "value"})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/test")

        assert res.success
        data = json.loads(res.output)
        assert data == {"key": "value"}
        assert "data" not in data

    @pytest.mark.asyncio
    async def test_missing_data_field_defaults_to_empty(self):
        orch = make_orchestrator()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={})
        response.text = AsyncMock(return_value="{}")
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/test")

        assert res.success
        data = json.loads(res.output)
        assert data == {}

    @pytest.mark.asyncio
    async def test_null_data_returns_failure(self):
        orch = make_orchestrator()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={"data": None})
        response.text = AsyncMock(return_value='{"data": null}')
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch._api_request("GET", "/api2/json/test")

        assert not res.success
        assert "null data" in res.error.lower()

    @pytest.mark.asyncio
    async def test_auth_headers_sent(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {})
        ctx = make_mock_ctx(response)
        orch._session = make_mock_session(ctx)

        await orch._api_request("GET", "/api2/json/test")

        call_kwargs = orch._session.request.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "PVEAPIToken=user@pam!test-token=secret-token-value"

    @pytest.mark.asyncio
    async def test_url_constructed_correctly(self):
        orch = make_orchestrator(api_url="https://pve.example.com:8006/")
        response = make_mock_response(200, {})
        orch._session = make_mock_session(make_mock_ctx(response))

        await orch._api_request("GET", "/api2/json/nodes/pve/qemu/100/status/current")

        call_args = orch._session.request.call_args
        method = call_args.args[0]
        url = call_args.args[1]
        assert method == "GET"
        assert url == "https://pve.example.com:8006/api2/json/nodes/pve/qemu/100/status/current"

    @pytest.mark.asyncio
    async def test_post_data_passed_to_session(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {})
        orch._session = make_mock_session(make_mock_ctx(response))

        payload = {"file": "/tmp/test.sh", "content": "aGVsbG8=", "encode": True}
        await orch._api_request("POST", "/api2/json/nodes/pve/qemu/100/agent/file-write", data=payload)

        call_kwargs = orch._session.request.call_args.kwargs
        assert call_kwargs["data"] == payload


# ---------------------------------------------------------------------------
# _wait_for_task tests
# ---------------------------------------------------------------------------

class TestWaitForTask:

    @pytest.mark.asyncio
    async def test_task_completes_successfully(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        orch._session = make_mock_session(make_mock_ctx(response))

        result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is True

    @pytest.mark.asyncio
    async def test_task_fails_nonzero_exitcode(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "stopped", "exitcode": 1})
        orch._session = make_mock_session(make_mock_ctx(response))

        result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_task_still_running_then_completes(self):
        orch = make_orchestrator()
        running_response = make_mock_response(200, {"status": "running"})
        done_response = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        orch._session = make_mock_session([
            make_mock_ctx(running_response),
            make_mock_ctx(done_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is True

    @pytest.mark.asyncio
    async def test_task_still_running_then_fails(self):
        orch = make_orchestrator()
        running_response = make_mock_response(200, {"status": "running"})
        failed_response = make_mock_response(200, {"status": "stopped", "exitcode": 2})
        orch._session = make_mock_session([
            make_mock_ctx(running_response),
            make_mock_ctx(failed_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_task_status_poll_failure(self):
        orch = make_orchestrator()
        error_response = make_mock_response(500, {"errors": "task not found"})
        orch._session = make_mock_session(make_mock_ctx(error_response))

        result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        orch = make_orchestrator()
        running_response = make_mock_response(200, {"status": "running"})
        orch._session = make_mock_session(make_mock_ctx(running_response))

        with patch("asyncio.sleep", new=AsyncMock()):
            result = await orch._wait_for_task("UPID:pve:00001234:abc", timeout=0)
        assert result is False

    @pytest.mark.asyncio
    async def test_task_missing_exitcode(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "stopped"})
        orch._session = make_mock_session(make_mock_ctx(response))

        result = await orch._wait_for_task("UPID:pve:00001234:abc")
        assert result is False

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(self):
        orch = make_orchestrator()
        running1 = make_mock_response(200, {"status": "running"})
        running2 = make_mock_response(200, {"status": "running"})
        done = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        orch._session = make_mock_session([
            make_mock_ctx(running1),
            make_mock_ctx(running2),
            make_mock_ctx(done),
        ])

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", new=mock_sleep):
            result = await orch._wait_for_task("UPID:pve:00001234:abc")

        assert result is True
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0

    @pytest.mark.asyncio
    async def test_backoff_capped_at_5s(self):
        orch = make_orchestrator()
        responses = [make_mock_ctx(make_mock_response(200, {"status": "running"})) for _ in range(6)]
        responses.append(make_mock_ctx(make_mock_response(200, {"status": "stopped", "exitcode": 0})))
        orch._session = make_mock_session(responses)

        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch("asyncio.sleep", new=mock_sleep):
            result = await orch._wait_for_task("UPID:pve:00001234:abc")

        assert result is True
        assert len(sleep_calls) == 6
        assert sleep_calls[0] == 1.0
        assert sleep_calls[1] == 2.0
        assert sleep_calls[2] == 4.0
        assert sleep_calls[3] == 5.0
        assert sleep_calls[4] == 5.0
        assert sleep_calls[5] == 5.0


# ---------------------------------------------------------------------------
# revert_to_checkpoint / start_vm / stop_vm (with task polling)
# ---------------------------------------------------------------------------

class TestLifecycleWithTaskPolling:

    @pytest.mark.asyncio
    async def test_revert_to_checkpoint_success(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00001234:abc"
        rollback_response = make_mock_response(200, upid)
        task_response = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        orch._session = make_mock_session([
            make_mock_ctx(rollback_response),
            make_mock_ctx(task_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.revert_to_checkpoint("LabServer01", "baseline")

        assert res.success
        assert json.loads(res.output) == upid

    @pytest.mark.asyncio
    async def test_revert_to_checkpoint_task_failure(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00001234:abc"
        rollback_response = make_mock_response(200, upid)
        task_response = make_mock_response(200, {"status": "stopped", "exitcode": 1})
        orch._session = make_mock_session([
            make_mock_ctx(rollback_response),
            make_mock_ctx(task_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.revert_to_checkpoint("LabServer01", "baseline")

        assert not res.success
        assert "failed" in res.error.lower()

    @pytest.mark.asyncio
    async def test_revert_to_checkpoint_api_error(self):
        orch = make_orchestrator()
        error_response = make_mock_response(404, {"errors": "snapshot not found"})
        orch._session = make_mock_session(make_mock_ctx(error_response))

        res = await orch.revert_to_checkpoint("LabServer01", "nonexistent")

        assert not res.success
        assert "HTTP 404" in res.error

    @pytest.mark.asyncio
    async def test_start_vm_success(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00005678:def"
        start_response = make_mock_response(200, upid)
        task_response = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        orch._session = make_mock_session([
            make_mock_ctx(start_response),
            make_mock_ctx(task_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.start_vm("LabServer01")

        assert res.success
        assert json.loads(res.output) == upid

    @pytest.mark.asyncio
    async def test_start_vm_task_failure(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00005678:def"
        start_response = make_mock_response(200, upid)
        task_response = make_mock_response(200, {"status": "stopped", "exitcode": 1})
        orch._session = make_mock_session([
            make_mock_ctx(start_response),
            make_mock_ctx(task_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.start_vm("LabServer01")

        assert not res.success
        assert "failed" in res.error.lower()

    @pytest.mark.asyncio
    async def test_stop_vm_force_uses_stop_action(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00009999:ghi"
        stop_response = make_mock_response(200, upid)
        task_response = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        session = make_mock_session([
            make_mock_ctx(stop_response),
            make_mock_ctx(task_response),
        ])
        orch._session = session

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.stop_vm("LabServer01", force=True)

        assert res.success
        call_args = session.request.call_args_list[0]
        url = call_args.args[1]
        assert "/status/stop" in url

    @pytest.mark.asyncio
    async def test_stop_vm_graceful_uses_shutdown_action(self):
        orch = make_orchestrator()
        upid = "UPID:pve:00009999:ghi"
        stop_response = make_mock_response(200, upid)
        task_response = make_mock_response(200, {"status": "stopped", "exitcode": 0})
        session = make_mock_session([
            make_mock_ctx(stop_response),
            make_mock_ctx(task_response),
        ])
        orch._session = session

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.stop_vm("LabServer01", force=False)

        assert res.success
        call_args = session.request.call_args_list[0]
        url = call_args.args[1]
        assert "/status/shutdown" in url

    @pytest.mark.asyncio
    async def test_start_vm_api_error(self):
        orch = make_orchestrator()
        error_response = make_mock_response(403, {"errors": "permission denied"})
        orch._session = make_mock_session(make_mock_ctx(error_response))

        res = await orch.start_vm("LabServer01")

        assert not res.success
        assert "HTTP 403" in res.error

    @pytest.mark.asyncio
    async def test_checkpoint_name_url_encoded(self):
        orch = make_orchestrator()
        error_response = make_mock_response(404, {"errors": "not found"})
        session = make_mock_session(make_mock_ctx(error_response))
        orch._session = session

        await orch.revert_to_checkpoint("LabServer01", "my snapshot/test")

        call_args = session.request.call_args
        url = call_args.args[1]
        assert "my%20snapshot%2Ftest" in url


# ---------------------------------------------------------------------------
# get_vm_ip tests (IP parsing)
# ---------------------------------------------------------------------------

class TestGetVmIp:

    @pytest.mark.asyncio
    async def test_returns_first_non_loopback_ipv4(self):
        orch = make_orchestrator()
        interfaces = [
            {"name": "lo", "hwaddr": "00:00:00:00:00:00", "ip-addresses": [
                {"ip-address-type": "ipv4", "ip-address": "127.0.0.1", "prefix": 8},
            ]},
            {"name": "eth0", "hwaddr": "52:54:00:12:34:56", "ip-addresses": [
                {"ip-address-type": "ipv4", "ip-address": "192.168.100.50", "prefix": 24},
                {"ip-address-type": "ipv6", "ip-address": "fe80::5054:ff:fe12:3456", "prefix": 64},
            ]},
        ]
        response = make_mock_response(200, interfaces)
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_ip("LabServer01")

        assert res.success
        assert res.output == "192.168.100.50"

    @pytest.mark.asyncio
    async def test_skips_ipv6_addresses(self):
        orch = make_orchestrator()
        interfaces = [
            {"name": "eth0", "ip-addresses": [
                {"ip-address-type": "ipv6", "ip-address": "fe80::1", "prefix": 64},
                {"ip-address-type": "ipv4", "ip-address": "10.0.0.5", "prefix": 24},
            ]},
        ]
        response = make_mock_response(200, interfaces)
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_ip("LabServer01")

        assert res.success
        assert res.output == "10.0.0.5"

    @pytest.mark.asyncio
    async def test_no_ipv4_addresses(self):
        orch = make_orchestrator()
        interfaces = [
            {"name": "eth0", "ip-addresses": [
                {"ip-address-type": "ipv6", "ip-address": "fe80::1", "prefix": 64},
            ]},
        ]
        response = make_mock_response(200, interfaces)
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_ip("LabServer01")

        assert not res.success
        assert "No non-loopback IPv4" in res.error

    @pytest.mark.asyncio
    async def test_only_loopback_addresses(self):
        orch = make_orchestrator()
        interfaces = [
            {"name": "lo", "ip-addresses": [
                {"ip-address-type": "ipv4", "ip-address": "127.0.0.1", "prefix": 8},
            ]},
        ]
        response = make_mock_response(200, interfaces)
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_ip("LabServer01")

        assert not res.success
        assert "No non-loopback IPv4" in res.error

    @pytest.mark.asyncio
    async def test_empty_interface_list(self):
        orch = make_orchestrator()
        response = make_mock_response(200, [])
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_ip("LabServer01")

        assert not res.success
        assert "No non-loopback IPv4" in res.error

    @pytest.mark.asyncio
    async def test_interface_with_no_ip_addresses(self):
        orch = make_orchestrator()
        interfaces = [
            {"name": "eth0", "hwaddr": "52:54:00:12:34:56"},
            {"name": "eth1", "ip-addresses": [
                {"ip-address-type": "ipv4", "ip-address": "172.16.0.10", "prefix": 24},
            ]},
        ]
        response = make_mock_response(200, interfaces)
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_ip("LabServer01")

        assert res.success
        assert res.output == "172.16.0.10"

    @pytest.mark.asyncio
    async def test_api_error_propagates(self):
        orch = make_orchestrator()
        error_response = make_mock_response(500, {"errors": "guest agent not running"})
        orch._session = make_mock_session(make_mock_ctx(error_response))

        res = await orch.get_vm_ip("LabServer01")

        assert not res.success
        assert "HTTP 500" in res.error

    @pytest.mark.asyncio
    async def test_uses_resolved_vmid_in_url(self):
        orch = make_orchestrator(vm_name_to_id={"WebServer": "200"})
        response = make_mock_response(200, [
            {"name": "eth0", "ip-addresses": [
                {"ip-address-type": "ipv4", "ip-address": "10.0.0.1", "prefix": 24},
            ]},
        ])
        session = make_mock_session(make_mock_ctx(response))
        orch._session = session

        await orch.get_vm_ip("WebServer")

        call_args = session.request.call_args
        url = call_args.args[1]
        assert "/qemu/200/" in url


# ---------------------------------------------------------------------------
# get_vm_state tests
# ---------------------------------------------------------------------------

class TestGetVmState:

    @pytest.mark.asyncio
    async def test_running_state(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "running", "vmid": 100})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_state("LabServer01")

        assert res.success
        assert res.output == "running"

    @pytest.mark.asyncio
    async def test_stopped_state(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "stopped", "vmid": 100})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_state("LabServer01")

        assert res.success
        assert res.output == "stopped"

    @pytest.mark.asyncio
    async def test_paused_state(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"status": "paused", "vmid": 100})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_state("LabServer01")

        assert res.success
        assert res.output == "paused"

    @pytest.mark.asyncio
    async def test_missing_status_field_returns_unknown(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {"vmid": 100, "name": "test-vm"})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.get_vm_state("LabServer01")

        assert res.success
        assert res.output == "unknown"

    @pytest.mark.asyncio
    async def test_api_error_propagates(self):
        orch = make_orchestrator()
        error_response = make_mock_response(404, {"errors": "VM not found"})
        orch._session = make_mock_session(make_mock_ctx(error_response))

        res = await orch.get_vm_state("LabServer01")

        assert not res.success
        assert "HTTP 404" in res.error

    @pytest.mark.asyncio
    async def test_uses_resolved_vmid_in_url(self):
        orch = make_orchestrator(vm_name_to_id={"DBServer": "300"})
        response = make_mock_response(200, {"status": "running"})
        session = make_mock_session(make_mock_ctx(response))
        orch._session = session

        await orch.get_vm_state("DBServer")

        call_args = session.request.call_args
        url = call_args.args[1]
        assert "/qemu/300/status/current" in url


# ---------------------------------------------------------------------------
# test_guest_connectivity
# ---------------------------------------------------------------------------

class TestGuestConnectivity:

    @pytest.mark.asyncio
    async def test_ping_success(self):
        orch = make_orchestrator()
        response = make_mock_response(200, {})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.test_guest_connectivity("LabServer01")

        assert res.success

    @pytest.mark.asyncio
    async def test_ping_error(self):
        orch = make_orchestrator()
        response = make_mock_response(503, {"errors": "guest agent not running"})
        orch._session = make_mock_session(make_mock_ctx(response))

        res = await orch.test_guest_connectivity("LabServer01")

        assert not res.success
        assert "HTTP 503" in res.error


# ---------------------------------------------------------------------------
# run_script_in_guest tests
# ---------------------------------------------------------------------------

class TestRunScriptInGuest:

    @pytest.mark.asyncio
    async def test_missing_script_file(self):
        orch = make_orchestrator()

        res = await orch.run_script_in_guest("LabServer01", "/nonexistent/script.sh")

        assert not res.success
        assert "Script not found" in res.error

    @pytest.mark.asyncio
    async def test_successful_execution(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test_script.sh"
        script.write_text('echo "hello world"')

        stdout_b64 = base64.b64encode(b'{"status":"correct"}').decode("ascii")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 1234})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
            "out-data": stdout_b64,
        })
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert res.success
        assert res.output == '{"status":"correct"}'

    @pytest.mark.asyncio
    async def test_script_exit_nonzero(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "failing.sh"
        script.write_text("exit 1")

        stderr_b64 = base64.b64encode(b"command failed").decode("ascii")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 5678})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 1,
            "out-data": "",
            "err-data": stderr_b64,
        })
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert not res.success
        assert "code 1" in res.error
        assert "command failed" in res.error

    @pytest.mark.asyncio
    async def test_file_write_failure(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        file_write_error = make_mock_response(403, {"errors": "permission denied"})
        orch._session = make_mock_session(make_mock_ctx(file_write_error))

        res = await orch.run_script_in_guest("LabServer01", str(script))

        assert not res.success
        assert "HTTP 403" in res.error

    @pytest.mark.asyncio
    async def test_exec_failure(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        file_write_response = make_mock_response(200, {})
        exec_error = make_mock_response(500, {"errors": "exec failed"})
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_error),
            make_mock_ctx(cleanup_response),
        ])

        res = await orch.run_script_in_guest("LabServer01", str(script))

        assert not res.success
        assert "HTTP 500" in res.error

    @pytest.mark.asyncio
    async def test_no_pid_returned(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {})
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(cleanup_response),
        ])

        res = await orch.run_script_in_guest("LabServer01", str(script))

        assert not res.success
        assert "No PID" in res.error

    @pytest.mark.asyncio
    async def test_polls_until_exited(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        stdout_b64 = base64.b64encode(b"done").decode("ascii")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 999})
        running_status = make_mock_response(200, {"exited": False})
        done_status = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
            "out-data": stdout_b64,
        })
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(running_status),
            make_mock_ctx(done_status),
            make_mock_ctx(cleanup_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert res.success
        assert res.output == "done"

    @pytest.mark.asyncio
    async def test_script_content_base64_encoded(self, tmp_path):
        orch = make_orchestrator()
        script_content = '#!/bin/bash\necho "test output"\n'
        script = tmp_path / "test_script.sh"
        script.write_text(script_content)

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 1})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
            "out-data": "",
        })
        cleanup_response = make_mock_response(200, {})
        session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])
        orch._session = session

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert res.success
        file_write_call = session.request.call_args_list[0]
        sent_data = file_write_call.kwargs["data"]
        assert sent_data["file"].startswith("/tmp/")
        assert sent_data["file"].endswith(".sh")
        decoded = base64.b64decode(sent_data["content"]).decode("utf-8")
        assert decoded == script_content
        assert sent_data["encode"] is True

    @pytest.mark.asyncio
    async def test_exec_command_uses_bash(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "myscript.sh"
        script.write_text("echo hi")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 1})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
            "out-data": "",
        })
        cleanup_response = make_mock_response(200, {})
        session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])
        orch._session = session

        with patch("asyncio.sleep", new=AsyncMock()):
            await orch.run_script_in_guest("LabServer01", str(script))

        exec_call = session.request.call_args_list[1]
        sent_data = exec_call.kwargs["data"]
        assert sent_data["command"][0] == "/bin/bash"
        assert sent_data["command"][1].startswith("/tmp/")
        assert sent_data["command"][1].endswith(".sh")

    @pytest.mark.asyncio
    async def test_execution_timeout(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "slow.sh"
        script.write_text("sleep 9999")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 42})
        running_ctx = make_mock_ctx(make_mock_response(200, {"exited": False}))
        cleanup_response = make_mock_response(200, {})

        session = MagicMock()
        session.closed = False
        session.request = MagicMock(side_effect=[
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
        ] + [running_ctx] * 10 + [make_mock_ctx(cleanup_response)])
        orch._session = session

        time_calls = [0]
        mock_loop = MagicMock()

        def mock_time():
            time_calls[0] += 1
            values = [0.0, 50.0, 150.0]
            return values[min(time_calls[0] - 1, len(values) - 1)]

        mock_loop.time = mock_time

        with patch("asyncio.sleep", new=AsyncMock()), \
             patch("asyncio.get_running_loop", return_value=mock_loop):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert not res.success
        assert "timed out" in res.error.lower()
        assert "pid=42" in res.error

    @pytest.mark.asyncio
    async def test_empty_stdout_output(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "noop.sh"
        script.write_text("true")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 1})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
            "out-data": "",
        })
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert res.success
        assert res.output == ""

    @pytest.mark.asyncio
    async def test_no_out_data_field(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "noop.sh"
        script.write_text("true")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 1})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
        })
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])

        with patch("asyncio.sleep", new=AsyncMock()):
            res = await orch.run_script_in_guest("LabServer01", str(script))

        assert res.success
        assert res.output == ""

    @pytest.mark.asyncio
    async def test_exec_status_api_error(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 99})
        exec_status_error = make_mock_response(500, {"errors": "internal error"})
        cleanup_response = make_mock_response(200, {})
        orch._session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_error),
            make_mock_ctx(cleanup_response),
        ])

        res = await orch.run_script_in_guest("LabServer01", str(script))

        assert not res.success
        assert "HTTP 500" in res.error

    @pytest.mark.asyncio
    async def test_cleanup_deletes_temp_file(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        file_write_response = make_mock_response(200, {})
        exec_response = make_mock_response(200, {"pid": 1})
        exec_status_response = make_mock_response(200, {
            "exited": True,
            "exitcode": 0,
            "out-data": "",
        })
        cleanup_response = make_mock_response(200, {})
        session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_response),
            make_mock_ctx(exec_status_response),
            make_mock_ctx(cleanup_response),
        ])
        orch._session = session

        with patch("asyncio.sleep", new=AsyncMock()):
            await orch.run_script_in_guest("LabServer01", str(script))

        cleanup_call = session.request.call_args_list[3]
        sent_data = cleanup_call.kwargs["data"]
        assert sent_data["command"][0] == "/bin/rm"
        assert sent_data["command"][1] == "-f"
        assert sent_data["command"][2].startswith("/tmp/")
        assert sent_data["command"][2].endswith(".sh")

    @pytest.mark.asyncio
    async def test_cleanup_runs_on_failure(self, tmp_path):
        orch = make_orchestrator()
        script = tmp_path / "test.sh"
        script.write_text("echo hi")

        file_write_response = make_mock_response(200, {})
        exec_error = make_mock_response(500, {"errors": "exec failed"})
        cleanup_response = make_mock_response(200, {})
        session = make_mock_session([
            make_mock_ctx(file_write_response),
            make_mock_ctx(exec_error),
            make_mock_ctx(cleanup_response),
        ])
        orch._session = session

        await orch.run_script_in_guest("LabServer01", str(script))

        assert len(session.request.call_args_list) == 3
        cleanup_call = session.request.call_args_list[2]
        sent_data = cleanup_call.kwargs["data"]
        assert sent_data["command"][0] == "/bin/rm"


# ---------------------------------------------------------------------------
# copy_file_to_guest tests
# ---------------------------------------------------------------------------

class TestCopyFileToGuest:

    @pytest.mark.asyncio
    async def test_missing_source_file(self):
        orch = make_orchestrator()

        res = await orch.copy_file_to_guest("LabServer01", "/nonexistent/file.txt", "/tmp/dst.txt")

        assert not res.success
        assert "Source not found" in res.error

    @pytest.mark.asyncio
    async def test_successful_copy(self, tmp_path):
        orch = make_orchestrator()
        source = tmp_path / "source.txt"
        source.write_bytes(b"file content here")

        response = make_mock_response(200, {})
        session = make_mock_session(make_mock_ctx(response))
        orch._session = session

        res = await orch.copy_file_to_guest("LabServer01", str(source), "/remote/path.txt")

        assert res.success
        call_args = session.request.call_args
        sent_data = call_args.kwargs["data"]
        assert sent_data["file"] == "/remote/path.txt"
        decoded = base64.b64decode(sent_data["content"]).decode("utf-8")
        assert decoded == "file content here"
        assert sent_data["encode"] is True

    @pytest.mark.asyncio
    async def test_binary_file_copy(self, tmp_path):
        orch = make_orchestrator()
        binary_data = bytes(range(256))
        source = tmp_path / "binary.dat"
        source.write_bytes(binary_data)

        response = make_mock_response(200, {})
        session = make_mock_session(make_mock_ctx(response))
        orch._session = session

        res = await orch.copy_file_to_guest("LabServer01", str(source), "/tmp/binary.dat")

        assert res.success
        call_args = session.request.call_args
        sent_data = call_args.kwargs["data"]
        decoded = base64.b64decode(sent_data["content"])
        assert decoded == binary_data

    @pytest.mark.asyncio
    async def test_api_error_on_copy(self, tmp_path):
        orch = make_orchestrator()
        source = tmp_path / "src.txt"
        source.write_text("hi")

        error_response = make_mock_response(403, {"errors": "write permission denied"})
        orch._session = make_mock_session(make_mock_ctx(error_response))

        res = await orch.copy_file_to_guest("LabServer01", str(source), "/remote/dst.txt")

        assert not res.success
        assert "HTTP 403" in res.error

    @pytest.mark.asyncio
    async def test_empty_file_copy(self, tmp_path):
        orch = make_orchestrator()
        source = tmp_path / "empty.txt"
        source.write_bytes(b"")

        response = make_mock_response(200, {})
        session = make_mock_session(make_mock_ctx(response))
        orch._session = session

        res = await orch.copy_file_to_guest("LabServer01", str(source), "/tmp/empty.txt")

        assert res.success
        call_args = session.request.call_args
        sent_data = call_args.kwargs["data"]
        decoded = base64.b64decode(sent_data["content"])
        assert decoded == b""

    @pytest.mark.asyncio
    async def test_uses_resolved_vmid(self, tmp_path):
        orch = make_orchestrator(vm_name_to_id={"FileServer": "400"})
        source = tmp_path / "src.txt"
        source.write_text("data")

        response = make_mock_response(200, {})
        session = make_mock_session(make_mock_ctx(response))
        orch._session = session

        await orch.copy_file_to_guest("FileServer", str(source), "/tmp/test.txt")

        call_args = session.request.call_args
        url = call_args.args[1]
        assert "/qemu/400/agent/file-write" in url


# ---------------------------------------------------------------------------
# close() / session lifecycle
# ---------------------------------------------------------------------------

class TestSessionLifecycle:

    @pytest.mark.asyncio
    async def test_close_closes_session(self):
        orch = make_orchestrator()
        mock_session = AsyncMock()
        mock_session.closed = False
        orch._session = mock_session

        await orch.close()

        mock_session.close.assert_called_once()
        assert orch._session is None

    @pytest.mark.asyncio
    async def test_close_when_session_is_none(self):
        orch = make_orchestrator()

        await orch.close()

        assert orch._session is None

    @pytest.mark.asyncio
    async def test_close_when_session_already_closed(self):
        orch = make_orchestrator()
        mock_session = MagicMock()
        mock_session.closed = True
        orch._session = mock_session

        await orch.close()

        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_session_creates_on_first_use(self):
        orch = make_orchestrator()
        assert orch._session is None

        with patch("app.orchestrator_proxmox.aiohttp.ClientSession") as mock_cs:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cs.return_value = mock_session

            session1 = await orch._get_session()
            assert session1 is mock_session
            assert orch._session is mock_session

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing(self):
        orch = make_orchestrator()
        mock_session = MagicMock()
        mock_session.closed = False
        orch._session = mock_session

        with patch("app.orchestrator_proxmox.aiohttp.ClientSession") as mock_cs:
            session = await orch._get_session()
            assert session is mock_session
            mock_cs.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_session_recreates_after_close(self):
        orch = make_orchestrator()
        mock_old_session = MagicMock()
        mock_old_session.closed = True
        orch._session = mock_old_session

        with patch("app.orchestrator_proxmox.aiohttp.ClientSession") as mock_cs:
            mock_new_session = MagicMock()
            mock_new_session.closed = False
            mock_cs.return_value = mock_new_session

            session = await orch._get_session()
            assert session is mock_new_session
            mock_cs.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_includes_timeout(self):
        orch = make_orchestrator()
        with patch("app.orchestrator_proxmox.aiohttp.ClientSession") as mock_cs:
            mock_session = MagicMock()
            mock_session.closed = False
            mock_cs.return_value = mock_session

            await orch._get_session()

            call_kwargs = mock_cs.call_args.kwargs
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"].total == 30

    @pytest.mark.asyncio
    async def test_close_sleeps_after_session_close(self):
        orch = make_orchestrator()
        mock_session = AsyncMock()
        mock_session.closed = False
        orch._session = mock_session

        with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await orch.close()

            mock_session.close.assert_called_once()
            assert orch._session is None
            mock_sleep.assert_called_with(0.25)


# ---------------------------------------------------------------------------
# _auth_headers
# ---------------------------------------------------------------------------

class TestAuthHeaders:

    def test_auth_header_format(self):
        orch = make_orchestrator(
            api_token_id="user@pam!my-token",
            api_token_secret="abc-123-secret",
        )
        headers = orch._auth_headers()
        assert headers["Authorization"] == "PVEAPIToken=user@pam!my-token=abc-123-secret"

    def test_auth_header_with_special_chars(self):
        orch = make_orchestrator(
            api_token_id="root@pam!token-with-dashes",
            api_token_secret="secret-with-special=chars",
        )
        headers = orch._auth_headers()
        assert "PVEAPIToken=" in headers["Authorization"]
        assert "root@pam!token-with-dashes" in headers["Authorization"]
        assert "secret-with-special=chars" in headers["Authorization"]

    def test_api_url_trailing_slash_stripped(self):
        orch = make_orchestrator(api_url="https://pve.test:8006/")
        assert orch.api_url == "https://pve.test:8006"

    def test_api_url_no_trailing_slash(self):
        orch = make_orchestrator(api_url="https://pve.test:8006")
        assert orch.api_url == "https://pve.test:8006"

    def test_verify_ssl_defaults_to_true(self):
        orch = ProxmoxOrchestrator(
            api_url="https://pve.test:8006",
            api_token_id="user@pam!token",
            api_token_secret="secret",
        )
        assert orch.verify_ssl is True

    def test_verify_ssl_can_be_disabled(self):
        orch = ProxmoxOrchestrator(
            api_url="https://pve.test:8006",
            api_token_id="user@pam!token",
            api_token_secret="secret",
            verify_ssl=False,
        )
        assert orch.verify_ssl is False
