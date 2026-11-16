"""Operator-only synthetic BAND admission, exercised without credentials/network."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.diwali.core import LocalTransport
from app.models import Product


@pytest.fixture
def operator(tmp_path, monkeypatch, request):
    credentials = tmp_path / "private-band.json"
    credentials.write_text(json.dumps({"room_id": "offline-room", "actors": {
        role: {"agent_id": f"offline-{role}", "api_key": f"offline-key-{role}"}
        for role in ("manager", "researcher", "skeptic", "builder")}}))
    credentials.chmod(0o600)
    for key in ("DIWALI_ENABLED", "DIWALI_OPERATOR_DEMO", "DIWALI_LIVE_AUTHORIZED", "BAND_ENABLED"):
        monkeypatch.setenv(key, "true")
    monkeypatch.setenv("BAND_CREDENTIALS_FILE", str(credentials))
    for key, value in getattr(request, "param", {}).items():
        monkeypatch.setenv(key, value)
    from app.db import database
    from app.main import create_app
    url = f"sqlite:///{tmp_path}/operator.db"
    with TestClient(create_app(url)) as client:
        seed = client.post("/api/demo/reset").json()
        _engine, factory = database(url)
        yield client, seed, factory
        _engine.dispose()


def test_band_operator_run_uses_async_transport_once_and_reports_distinct_source_mode(operator, monkeypatch):
    from app.diwali import band_bridge
    client, seed, _factory = operator
    calls = []

    class OfflineBandTransport(LocalTransport):
        mode = "band"
        last_receipt = None

        def __init__(self, credentials):
            super().__init__()

        async def __aenter__(self):
            calls.append("start")
            return self

        async def __aexit__(self, *args):
            calls.append("close")

        async def exchange(self, message, context):
            self.last_receipt = {"request_id": str(message.message_id), "result_id": str(message.task_id),
                                 "authenticated_sender": self.identities[message.recipient]}
            return super().exchange(message, context)

    monkeypatch.setattr(band_bridge, "BandTransport", OfflineBandTransport, raising=False)
    body = {"purchase_ids": seed["purchase_ids"], "mode": "demo", "collaboration_mode": "band",
            "idempotency_key": "operator-band"}
    response = client.post("/api/runs", json=body)
    assert response.status_code == 200, response.text
    identifier = response.json()["run_id"]
    same = client.post("/api/runs", json=body)
    assert same.json()["run_id"] == identifier
    assert calls == ["start", "close"]
    result = client.get(f"/api/runs/{identifier}").json()
    assert result["status"] == "completed"
    assert result["actual_transport"] == "band"
    assert result["source_mode"] == "recorded"
    assert result["reviewer_mode"] == "rules"
    assert result["summary"]["verified_matches"] == 1
    assert result["summary"]["rejected"] == 1
    assert result["summary"]["prepared_packets"] == 1
    messages = client.get(f"/api/runs/{identifier}/agent-messages").json()["items"]
    assert len(messages) == 18
    assert all(m["transport"] == "band" for m in messages)


def test_modified_synthetic_purchase_cannot_be_sent_to_band(operator):
    client, seed, factory = operator
    with factory.begin() as session:
        product = session.scalar(select(Product))
        product.payload = product.payload | {"product": product.payload["product"] | {"brand": "Private test data"}}
    response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"], "mode": "demo",
        "collaboration_mode": "band", "idempotency_key": "modified-fixture"})
    assert response.status_code == 422


@pytest.mark.parametrize("operator", [
    {"FINCH_ENABLED": "true", "LYZR_ENABLED": "false"},
    {"AGENT37_ENABLED": "true"},
    {"LYZR_ENABLED": "true", "LYZR_API_KEY": "", "LYZR_REVIEW_AGENT_ID": ""},
], indirect=True)
def test_enabled_unready_provider_is_rejected_before_any_sdk_start(operator, monkeypatch):
    from app.diwali import band_bridge
    client, seed, _factory = operator

    def unexpected_provider(*args, **kwargs):
        raise AssertionError("Unready sponsor profile reached SDK startup")

    monkeypatch.setattr(band_bridge, "BandTransport", unexpected_provider)
    response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"],
        "collaboration_mode": "band", "idempotency_key": "not-ready"})
    assert response.status_code == 503
