"""Public worker is useful offline even while Agent37 lifecycle remains blocked."""

import importlib
import json
from pathlib import Path

import httpx
import pytest


@pytest.fixture(autouse=True)
def public_dns_only(monkeypatch):
    import socket

    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs:
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))])


def worker():
    try:
        return importlib.import_module("app.diwali.research_worker")
    except ModuleNotFoundError:
        pytest.fail("Bounded public-source worker is not implemented")


async def test_worker_reads_only_fixed_public_query_and_returns_validated_record():
    module = worker()
    calls = []
    rows = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=rows)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        result = await module.research_public("26-792", client=http)
    assert result["record"]["models"] == ["ZHX-PB22"]
    assert result["record"]["mode"] == "live"
    assert result["source_provider"] == "cpsc"
    assert result["execution_mode"] == "local_worker"
    assert len(calls) == 1
    assert calls[0].url.host == "www.saferproducts.gov"
    assert dict(calls[0].url.params) == {"ProductName": "NEWDERY", "format": "json"}


@pytest.mark.parametrize("reference", ["https://evil.test", "http://127.0.0.1", "unknown-recall"])
async def test_worker_rejects_arbitrary_source_without_network(reference):
    module = worker()
    calls = []
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: calls.append(request))) as http:
        with pytest.raises(ValueError):
            await module.research_public(reference, client=http)
    assert calls == []


async def test_worker_source_outage_has_one_attempt():
    module = worker()
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        with pytest.raises(ValueError):
            await module.research_public("26-792", client=http)
    assert len(calls) == 1


@pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.1", "::1", "169.254.169.254"])
async def test_private_dns_is_rejected_before_official_source_request(monkeypatch, address):
    import socket

    module = worker()
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs:
        [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, 443))])
    calls = []

    def unexpected(request):
        calls.append(request)
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected)) as http:
        with pytest.raises(ValueError):
            await module.research_public("26-792", client=http)
    assert calls == []
