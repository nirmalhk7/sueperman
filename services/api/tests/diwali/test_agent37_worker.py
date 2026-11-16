"""Documented Agent37 exec/read/delete boundary; no real compute in tests."""

import importlib
import json
from pathlib import Path

import httpx
import pytest


def adapter():
    try:
        return importlib.import_module("app.diwali.agent37_worker")
    except ModuleNotFoundError:
        pytest.fail("Pinned Agent37 public-worker adapter is not implemented")


async def test_owned_worker_uses_documented_auth_returns_validated_source_and_deletes():
    module = adapter()
    requests = []
    rows = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())

    def respond(request):
        requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"exit_code": 0, "stdout": json.dumps({
                "reference": "26-792", "rows": rows, "worker_sha256": module.WORKER_SHA256}),
                "stderr": "", "truncated": False})
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "owned-synthetic", "deleted": True})
        return httpx.Response(404, json={"error": {"code": "not_found"}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        worker = module.Agent37Worker("offline-key", "owned-synthetic", client=http,
            owned_ids={"owned-synthetic"})
        result = await worker.run("synthetic-run", "synthetic-case")
        assert result["record"]["models"] == ["ZHX-PB22"]
        assert result["execution_mode"] == "agent37"
        with pytest.raises(ValueError, match="attempted"):
            await worker.run("synthetic-run", "synthetic-case")
        assert await worker.delete_and_confirm() is True
    assert len(requests) == 3
    assert str(requests[0].url) == "https://sandbox.agent37.app/v1/instances/owned-synthetic/exec"
    assert requests[0].headers["X-Agent37-Key"] == "offline-key"
    body = json.loads(requests[0].content)
    assert body["background"] is False
    assert body["name"] == "sueperman-synthetic-run-synthetic-case"
    assert "offline-key" not in body["command"]
    assert requests[1].headers["Authorization"] == "Bearer offline-key"


@pytest.mark.parametrize("fault", ["exit", "truncated", "pin", "outage"])
async def test_worker_failure_has_one_attempt_and_no_invented_source(fault):
    module = adapter()
    requests = []
    rows = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())

    def respond(request):
        requests.append(request)
        if fault == "outage":
            return httpx.Response(503)
        return httpx.Response(200, json={"exit_code": 1 if fault == "exit" else 0,
            "stdout": json.dumps({"reference": "26-792", "rows": rows, "worker_sha256": "0" * 64 if fault == "pin" else module.WORKER_SHA256}),
            "stderr": "private detail", "truncated": fault == "truncated"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        worker = module.Agent37Worker("offline-key", "owned-synthetic", client=http,
            owned_ids={"owned-synthetic"})
        with pytest.raises(ValueError):
            await worker.run("synthetic-run", "synthetic-case")
    assert len(requests) == 1


def test_cannot_execute_or_delete_unowned_or_injected_instance():
    module = adapter()
    for identifier in ("someone-elses-instance", "../secrets", "https://evil.test"):
        with pytest.raises(ValueError):
            module.Agent37Worker("offline-key", identifier, owned_ids={"owned-synthetic"})


def test_remote_worker_source_rejects_private_dns_before_fetch(monkeypatch):
    import socket
    import urllib.request

    module = adapter()
    calls = []
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs:
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))])

    class NoNetwork:
        def open(self, *args, **kwargs):
            calls.append(1)
            raise ValueError("Unexpected network request")

    monkeypatch.setattr(urllib.request, "build_opener", lambda *args: NoNetwork())
    with pytest.raises(ValueError):
        exec(module.WORKER_SOURCE, {"EXPECTED_WORKER_SHA256": module.WORKER_SHA256})  # noqa: S102 -- reviewed constant only
    assert calls == []


async def test_workspace_key_cannot_leave_exact_owned_instance_endpoints():
    module = adapter()
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        worker = module.Agent37Worker("offline-key", "owned-synthetic", client=http,
            owned_ids={"owned-synthetic"})
        with pytest.raises(ValueError):
            await worker.request("GET", "https://evil.test/steal")
    assert calls == []
