"""Corrections must retain historical facts and require renewed packet review."""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.mark.parametrize("mode", ["deterministic", "local"])
def test_revision_recheck_keeps_history_and_revokes_export(tmp_path, monkeypatch, mode):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    with TestClient(create_app(f"sqlite:///{tmp_path}/test.db")) as c:
        seed = c.post("/api/demo/reset").json()
        product = c.get("/api/products").json()[0]
        def run(key):
            r = c.post("/api/runs", json={"purchase_ids": seed["purchase_ids"], "mode": "demo",
                     "collaboration_mode": mode, "idempotency_key": key})
            assert r.status_code == 200, r.text
            return c.get("/api/opportunities", params={"run_id": r.json()["run_id"]}).json()
        old = next(o for o in run("before") if o["status"] == "verified_match")
        path = "/api/claim-packets/" + c.post(f"/api/opportunities/{old['id']}/claim-packet").json()["id"]
        assert c.post(path + "/approve-local", json={"confirmed": True}).status_code == 200
        url = f"/api/products/{product['id']}/corrections"
        body = {"confirmed": True, "model_number": "ZHX-PB23"}
        changed = c.post(url, json=body)
        assert changed.status_code == 200, changed.text
        assert c.post(url, json=body).json()["id"] == changed.json()["id"]
        assert len(c.get("/api/products").json()) == 5
        assert c.post(path + "/export").status_code == 409
        assert c.post(path + "/approve-local", json={"confirmed": True}).status_code == 409
        detail = c.get(f"/api/opportunities/{old['id']}").json()
        assert detail["product"]["product"]["model_number"] == "ZHX-PB22"
        assert detail["stale"] is True
        assert all(o["status"] != "verified_match" for o in run("after"))
        back = c.post(f"/api/products/{changed.json()['id']}/corrections",
                      json={"confirmed": True, "model_number": "ZHX-PB22"})
        assert back.status_code == 200
        fresh = next(o for o in run("restored") if o["status"] == "verified_match")
        assert fresh["id"] != old["id"]
        new_path = "/api/claim-packets/" + c.post(f"/api/opportunities/{fresh['id']}/claim-packet").json()["id"]
        assert c.post(new_path + "/export").status_code == 409
        assert c.post(new_path + "/approve-local", json={"confirmed": True}).status_code == 200
        assert c.post(new_path + "/export").status_code == 200


def test_active_run_and_unconfirmed_correction_are_refused(tmp_path):
    from app.db import database
    from app.models import AgentRun
    url = f"sqlite:///{tmp_path}/test.db"
    with TestClient(create_app(url)) as c:
        seed = c.post("/api/demo/reset").json()
        product = c.get("/api/products").json()[0]
        endpoint = f"/api/products/{product['id']}/corrections"
        assert c.post(endpoint, json={"confirmed": False, "model_number": "ZHX-PB23"}).status_code == 422
        engine, factory = database(url)
        with factory.begin() as s:
            s.add(AgentRun(idempotency_key="active", status="running",
                           payload={"purchase_ids": seed["purchase_ids"]}))
        assert c.post(endpoint, json={"confirmed": True, "model_number": "ZHX-PB23"}).status_code == 409
        engine.dispose()


def test_team_investigation_blocks_correction(tmp_path):
    from app.db import database
    from app.models import CaseRecord, CollaborationRun
    url = f"sqlite:///{tmp_path}/test.db"
    with TestClient(create_app(url)) as c:
        c.post("/api/demo/reset")
        product = c.get("/api/products").json()[0]
        engine, factory = database(url)
        with factory.begin() as s:
            case = CaseRecord(product_id=product["id"])
            s.add(case)
            s.flush()
            s.add(CollaborationRun(case_id=case.id, revision=1, idempotency_key="team", status="investigating"))
        response = c.post(f"/api/products/{product['id']}/corrections",
                          json={"confirmed": True, "model_number": "ZHX-PB23"})
        assert response.status_code == 409
        engine.dispose()


def test_corrected_team_case_cannot_export_or_restart_old_facts(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/test.db")) as c:
        c.post("/api/demo/reset")
        product = c.get("/api/products").json()[0]
        body = {"product_ids": [product["id"]], "idempotency_key": "team"}
        started = c.post("/api/collaborations", json=body).json()
        path = "/api/collaborations/" + started["id"]
        assert c.post(path + "/approve-local", json={"confirmed": True}).status_code == 200
        assert c.post(f"/api/products/{product['id']}/corrections",
                      json={"confirmed": True, "model_number": "ZHX-PB23"}).status_code == 200
        assert c.post(path + "/export").status_code == 409
        assert c.post("/api/collaborations", json=body | {"idempotency_key": "another"}).status_code == 409


def test_demo_reset_retains_current_revision_for_historical_team_purchase(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path}/test.db")) as c:
        c.post("/api/demo/reset")
        product = c.get("/api/products").json()[0]
        c.post("/api/collaborations", json={"product_ids": [product["id"]], "idempotency_key": "history"})
        c.post(f"/api/products/{product['id']}/corrections",
               json={"confirmed": True, "model_number": "ZHX-PB23"})
        reset = c.post("/api/demo/reset")
        assert reset.status_code == 200
        selected = reset.json()["product_ids"]
        products = [p for p in c.get("/api/products").json() if p["id"] in selected]
        assert sum(p["product"]["model_number"] == "ZHX-PB22" for p in products) == 1


def test_legacy_confirmation_cannot_edit_superseded_receipt_facts(tmp_path):
    from app.db import database
    from app.models import Product
    url = f"sqlite:///{tmp_path}/test.db"
    with TestClient(create_app(url)) as c:
        c.post("/api/demo/reset")
        product = c.get("/api/products").json()[0]
        engine, factory = database(url)
        with factory.begin() as s:
            record = s.get(Product, product["id"])
            record.payload = record.payload | {"source_type": "image"}
        body = {"confirmed": True, "model_number": "ZHX-PB23"}
        assert c.post(f"/api/products/{product['id']}/corrections", json=body).status_code == 200
        assert c.post(f"/api/products/{product['id']}/confirm-identifiers", json=body).status_code == 409
        engine.dispose()
