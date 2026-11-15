"""Existing run and packet routes remain authoritative in the app slice."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    with TestClient(create_app(f"sqlite:///{tmp_path}/api.db")) as client:
        yield client


def run(client, key="local", **extra):
    seed = client.post("/api/demo/reset").json()
    response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"], "mode": "demo",
        "collaboration_mode": "local", "idempotency_key": key} | extra)
    assert response.status_code == 200, response.text
    return client.get(f"/api/runs/{response.json()['run_id']}").json(), seed


def test_default_compatibility(client):
    seed = client.post("/api/demo/reset").json()
    body = {"purchase_ids": seed["purchase_ids"], "mode": "demo", "idempotency_key": "default"}
    first = client.post("/api/runs", json=body).json()
    same = client.post("/api/runs", json=body | {"collaboration_mode": "deterministic"})
    assert same.status_code == 200
    assert same.json()["run_id"] == first["run_id"]
    assert "collaboration_mode" not in same.json()
    messages = client.get(f"/api/runs/{first['run_id']}/agent-messages")
    assert messages.status_code == 200
    assert messages.json() == {"items": [], "next_seq": 0}


def test_idempotency_modes(client):
    seed = client.post("/api/demo/reset").json()
    body = {"purchase_ids": seed["purchase_ids"], "mode": "demo", "idempotency_key": "collision"}
    first = client.post("/api/runs", json=body)
    assert first.status_code == 200
    assert client.post("/api/runs", json=body | {"collaboration_mode": "local"}).status_code == 409
    assert client.post("/api/runs", json=body | {"fallback_of": first.json()["run_id"]}).status_code == 409


def test_feature_off_parity(tmp_path, monkeypatch):
    monkeypatch.setenv("DIWALI_ENABLED", "false")
    with TestClient(create_app(f"sqlite:///{tmp_path}/off.db")) as client:
        seed = client.post("/api/demo/reset").json()
        body = {"purchase_ids": seed["purchase_ids"], "idempotency_key": "disabled"}
        assert client.post("/api/runs", json=body | {"collaboration_mode": "local"}).status_code == 403
        response = client.post("/api/runs", json=body)
        assert response.status_code == 200
        result = client.get(f"/api/runs/{response.json()['run_id']}").json()
        assert result["summary"]["verified_matches"] == 1
        assert result["summary"]["rejected"] == 1
        assert result["summary"]["needs_review"] == 1
        assert result["summary"]["simulated_settlements"] == 1


def test_unapproved_export(client):
    result, _ = run(client)
    opportunities = client.get("/api/opportunities", params={"run_id": result["run_id"]}).json()
    exact = next(o for o in opportunities if o["status"] == "verified_match")
    packet = client.post(f"/api/opportunities/{exact['id']}/claim-packet")
    assert packet.status_code == 200
    assert packet.json()["approved_at"] is None
    path = f"/api/claim-packets/{packet.json()['id']}"
    assert client.post(path + "/export").status_code == 409
    assert client.post(path + "/approve-local", json={"confirmed": True}).status_code == 200
    exported = client.post(path + "/export")
    assert exported.status_code == 200
    assert "ZHX-PB22" in exported.text
    assert "not an external submission" in exported.text
    for o in opportunities:
        if o["id"] != exact["id"]:
            assert client.post(f"/api/opportunities/{o['id']}/claim-packet").status_code == 409


def test_provenance(client):
    result, _ = run(client)
    assert result["status"] == "completed"
    assert result["collaboration_mode"] == "local"
    assert result["actual_transport"] == "local"
    assert result["source_mode"] == "recorded"
    assert result["summary"]["rejected"] == 1
    assert result["summary"]["needs_review"] == 1
    assert result["summary"]["simulated_settlements"] == 1
    messages = client.get(f"/api/runs/{result['run_id']}/agent-messages").json()
    assert len(messages["items"]) == 18  # 6 + 4 + 2 + 4 + 2
    assert [m["seq"] for m in messages["items"]] == list(range(1, 19))
    assert "order_reference_redacted" not in json.dumps(messages)
    assert "merchant" not in json.dumps(messages)
    page = client.get(f"/api/runs/{result['run_id']}/agent-messages?after_seq=5&limit=2").json()
    assert [m["seq"] for m in page["items"]] == [6, 7]
    assert page["next_seq"] == 7
    assert client.get(f"/api/runs/{result['run_id']}/agent-messages?limit=101").status_code == 422
    assert client.get("/api/runs/nonexistent/agent-messages").status_code == 404


def test_unavailable_band_cannot_fall_back(client):
    seed = client.post("/api/demo/reset").json()
    response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"],
        "idempotency_key": "band", "collaboration_mode": "band"})
    assert response.status_code == 503


def test_status_is_cached_not_provider_execution(client):
    response = client.get("/api/integrations/diwali/status")
    assert response.status_code == 200
    assert response.json()["enabled"] is True
    assert all(p["healthy"] is None for p in response.json()["providers"])


def test_local_transport_refuses_live_mode(client):
    seed = client.post("/api/demo/reset").json()
    response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"], "mode": "live",
        "idempotency_key": "private", "collaboration_mode": "local"})
    assert response.status_code == 422


@pytest.mark.parametrize("changed", ["product", "source"])
def test_packet_routes_reject_changed_input(client, tmp_path, changed):
    from sqlalchemy import select

    from app.db import database
    from app.models import Product, SourceEvidence
    result, _ = run(client)
    opportunities = client.get("/api/opportunities", params={"run_id": result["run_id"]}).json()
    exact = next(o for o in opportunities if o["status"] == "verified_match")
    packet = client.post(f"/api/opportunities/{exact['id']}/claim-packet").json()
    path = f"/api/claim-packets/{packet['id']}"
    assert client.post(path + "/approve-local", json={"confirmed": True}).status_code == 200
    engine, factory = database(f"sqlite:///{tmp_path}/api.db")
    with factory.begin() as session:
        if changed == "product":
            product = session.get(Product, exact["product_id"])
            product.payload = product.payload | {"product": product.payload["product"] | {"model_number": "ZHX-PB23"}}
        else:
            source = session.scalar(select(SourceEvidence).where(SourceEvidence.opportunity_id == exact["id"]))
            source.payload = source.payload | {"quoted_excerpt": "Changed official model restriction"}
    assert client.post(path + "/export").status_code == 409
    assert client.post(path + "/approve-local", json={"confirmed": True}).status_code == 409
    assert client.get(path).json()["approved_at"] is None
    engine.dispose()


def test_configured_provider_does_not_imply_healthy(tmp_path, monkeypatch):
    monkeypatch.setenv("LYZR_API_KEY", "offline-test-key")
    monkeypatch.setenv("LYZR_REVIEW_AGENT_ID", "offline-review-agent")
    with TestClient(create_app(f"sqlite:///{tmp_path}/config.db")) as client:
        status = client.get("/api/integrations/diwali/status").json()
        provider = next(p for p in status["providers"] if p["name"] == "lyzr")
        assert provider["configured"] is True
        assert provider["enabled"] is False
        assert provider["healthy"] is None


def test_duplicate_purchase_ids_rejected_before_work(client):
    seed = client.post("/api/demo/reset").json()
    response = client.post("/api/runs", json={"purchase_ids": [seed["purchase_ids"][0]] * 2,
        "idempotency_key": "duplicate-product", "collaboration_mode": "local"})
    assert response.status_code == 422


def test_operator_reset_requires_isolated_explicit_opt_in(client):
    assert client.post("/api/demo/diwali/reset").status_code == 403


def test_operator_reset_reuses_original_seed(tmp_path, monkeypatch):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    monkeypatch.setenv("DIWALI_OPERATOR_DEMO", "true")
    with TestClient(create_app(f"sqlite:///{tmp_path}/isolated.db")) as client:
        first = client.post("/api/demo/diwali/reset")
        second = client.post("/api/demo/diwali/reset")
        assert first.status_code == second.status_code == 200
        assert len(first.json()["product_ids"]) == 5
        assert second.json()["product_ids"] == first.json()["product_ids"]


def test_explicit_fallback_creates_new_run_and_preserves_failure(client, monkeypatch):
    def fail(*args):
        raise ConnectionError("injected offline transport outage")
    monkeypatch.setattr("app.diwali.core.actor_reply", fail)
    failed, seed = run(client, key="failed-local")
    assert failed["status"] == "failed"
    fallback = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"], "mode": "demo",
        "collaboration_mode": "deterministic", "fallback_of": failed["run_id"], "idempotency_key": "explicit-fallback"})
    assert fallback.status_code == 200
    current = client.get(f"/api/runs/{fallback.json()['run_id']}").json()
    assert current["status"] == "completed"
    assert current["fallback_of"] == failed["run_id"]
    assert current["run_id"] != failed["run_id"]
    assert client.get(f"/api/runs/{failed['run_id']}").json()["status"] == "failed"
