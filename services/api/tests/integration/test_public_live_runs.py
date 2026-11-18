"""Public live investigations must never silently substitute recorded results."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/public.db")) as client:
        yield client


def imported(client):
    response = client.post("/api/uploads/purchases", files={"file": (
        "purchase.csv",
        (b"order_id,purchased_at,merchant,product_name,brand,model_number\n"
        b"REAL-1,2024-06-12,Store,Portable Power Bank,NEWDERY,ZHX-PB22\n"),
        "text/csv",
    )})
    assert response.status_code == 200
    return response.json()["purchase_ids"]


def test_public_live_run_does_not_fall_back_when_provider_disabled(client):
    response = client.post("/api/runs", json={
        "purchase_ids": imported(client), "mode": "live",
        "allow_recorded_fallback": False, "idempotency_key": "no-recording",
    })
    assert response.status_code == 200
    result = client.get(f"/api/runs/{response.json()['run_id']}").json()
    assert result["status"] == "failed"
    assert result["opportunities"] == []
    assert "replay" not in str(result["provider_modes"])


def test_public_live_run_rejects_synthetic_purchases(client):
    identifiers = client.post("/api/demo/reset").json()["purchase_ids"]
    result = client.post("/api/runs", json={
        "purchase_ids": identifiers, "mode": "live",
        "allow_recorded_fallback": False, "idempotency_key": "real-only",
    })
    assert result.status_code == 422


def test_fallback_policy_is_part_of_idempotent_input(client):
    identifiers = imported(client)
    request = {"purchase_ids": identifiers, "mode": "live", "idempotency_key": "policy"}
    assert client.post("/api/runs", json=request).status_code == 200
    assert client.post("/api/runs", json=request | {"allow_recorded_fallback": False}).status_code == 409


def test_real_team_admission_reports_disabled_configuration_without_starting_replay(client):
    purchases = imported(client)
    products = client.get("/api/products").json()
    product_id = next(p["id"] for p in products if p["purchase_id"] == purchases[0])
    response = client.post("/api/collaborations", json={"product_ids": [product_id],
        "mode": "live", "idempotency_key": "disabled-team"})
    assert response.status_code == 503
