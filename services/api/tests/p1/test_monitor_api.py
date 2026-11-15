"""Monitor controls require both user intent and operator capability."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from monitor_helpers import NOW, enable, monitor
from sqlalchemy import select


def app_client(tmp_path, monkeypatch, *, enabled=True, permitted=False):
    monkeypatch.setenv("P1_ENABLED", str(enabled).lower())
    monkeypatch.setenv("P1_MONITOR_ENABLED", str(permitted).lower())
    monkeypatch.setenv("CPSC_LIVE_ENABLED", str(permitted).lower())
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/default.db")
    from app.main import create_app
    return TestClient(create_app(database_url=f"sqlite:///{tmp_path}/api.db"))


def seeded_opportunity(client):
    purchases = client.post("/api/demo/reset").json()["purchase_ids"]
    run = client.post("/api/runs", json={"purchase_ids": purchases, "mode": "demo",
        "idempotency_key": "watch-api"}).json()
    return next(o for o in client.get("/api/opportunities", params={"run_id": run["run_id"]}).json()
                if o["status"] == "verified_match")


def test_disabled_p1_has_no_monitor_mutations(tmp_path, monkeypatch):
    with app_client(tmp_path, monkeypatch, enabled=False) as client:
        status = client.get("/api/p1/status")
        assert status.status_code == 200 and status.json()["enabled"] is False
        assert client.post("/api/opportunities/missing/source-monitor", json={"enabled": True}).status_code == 403


def test_watch_requires_operator_public_read_permission(tmp_path, monkeypatch):
    with app_client(tmp_path, monkeypatch) as client:
        opportunity = seeded_opportunity(client)
        path = f"/api/opportunities/{opportunity['id']}/source-monitor"
        response = client.post(path, json={"enabled": True})
        assert response.status_code == 503
        current = client.get(path).json()
        assert current["enabled"] is False and current["checks"] == []
        assert current["available"] is False


def test_enable_is_idempotent_disable_and_unknown_fields_are_safe(tmp_path, monkeypatch):
    with app_client(tmp_path, monkeypatch, permitted=True) as client:
        opportunity = seeded_opportunity(client)
        path = f"/api/opportunities/{opportunity['id']}/source-monitor"
        first = client.post(path, json={"enabled": True})
        assert first.status_code == 200
        assert first.json()["enabled"] is True and first.json()["interval_hours"] == 24
        second = client.post(path, json={"enabled": True})
        assert second.json()["id"] == first.json()["id"]
        assert client.post(path, json={"enabled": "false"}).status_code == 422
        assert client.post(path, json={"enabled": True, "url": "https://evil.example"}).status_code == 422
        disabled = client.post(path, json={"enabled": False})
        assert disabled.status_code == 200 and disabled.json()["enabled"] is False
        assert client.get(path).json()["enabled"] is False


@pytest.mark.asyncio
async def test_scheduler_drives_due_checks_and_stops_without_an_extra_read(graph):
    module = monitor()
    engine, factory, _client, opportunity_id, _packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    stopped = asyncio.Event()
    calls = []
    async def checker(reference):
        calls.append(reference)
        stopped.set()
        return record
    try:
        async with asyncio.timeout(1):
            await module.watch_loop(factory, stopped, checker=checker, clock=lambda: NOW, poll_seconds=0.001)
    except AttributeError:
        pytest.fail("Persistent watches have no running scheduler")
    assert calls == ["26-792"]
    with factory() as session:
        assert session.scalar(select(module.SourceCheck)).payload["status"] == "unchanged"


@pytest.mark.asyncio
async def test_public_checker_uses_registered_query_not_purchase_data(tmp_path, monkeypatch):
    import json
    from pathlib import Path

    import respx

    module = monitor()
    raw = json.loads((Path(__file__).parents[1] / "fixtures/p1-recalls/26610.json").read_text())
    with respx.mock as remote:
        route = remote.get("https://www.saferproducts.gov/RestWebServices/Recall",
                           params={"ProductName": "Flaunt", "format": "json"}).respond(200, json=[raw])
        try:
            result = await module.fetch_public("26-610")
        except AttributeError:
            pytest.fail("Scheduled watches cannot retrieve their official source")
        assert result.models == ["E33A"] and result.mode == "live"
        assert route.call_count == 1
        with pytest.raises(ValueError):
            await module.fetch_public("unknown-private-purchase")
