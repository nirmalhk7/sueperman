"""The opt-in normalizers must reach real upload/run/evidence/export behavior."""

import json
from pathlib import Path

import pytest
import respx
from fastapi.testclient import TestClient


@pytest.mark.parametrize("number,brand,model", [("26610", "Flaunt", "E33A"),
                                               ("25390", "iStore", "IST-09991/W05")])
def test_p1_live_import_uses_reviewed_normalizer_and_local_export(tmp_path, monkeypatch, number, brand, model):
    monkeypatch.setenv("P1_ENABLED", "true")
    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/default.db")
    from app.main import create_app

    row = json.loads((Path(__file__).parents[1] / f"fixtures/p1-recalls/{number}.json").read_text())
    csv = ("order_id,purchased_at,merchant,product_name,brand,model_number,upc\n"
           f"P1-SYNTHETIC,2024-09-01,Demo shop,Magnetic power bank,{brand},{model},\n").encode()
    with respx.mock as remote, TestClient(create_app(database_url=f"sqlite:///{tmp_path}/test.db")) as client:
        remote.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=[row])
        uploaded = client.post("/api/uploads/purchases", files={"file": ("p1.csv", csv, "text/csv")})
        assert uploaded.status_code == 200
        run = client.post("/api/runs", json={"purchase_ids": uploaded.json()["purchase_ids"],
            "mode": "live", "idempotency_key": "p1-normalizer"})
        assert run.status_code == 200
        run_id = run.json()["run_id"]
        completed = client.get(f"/api/runs/{run_id}").json()
        assert completed["status"] == "completed"
        assert completed["summary"]["verified_matches"] == 1
        opportunity = client.get("/api/opportunities", params={"run_id": run_id}).json()[0]
        detail = client.get(f"/api/opportunities/{opportunity['id']}").json()
        assert detail["recall"]["models"] == [model]
        assert detail["evidence"][0]["url"] == row["URL"]
        packet = client.post(f"/api/opportunities/{opportunity['id']}/claim-packet").json()
        assert client.post(f"/api/claim-packets/{packet['id']}/export").status_code == 409
        assert client.post(f"/api/claim-packets/{packet['id']}/approve-local", json={"confirmed": True}).status_code == 200
        exported = client.post(f"/api/claim-packets/{packet['id']}/export")
        assert exported.status_code == 200
        assert row["URL"] in exported.text
        assert "not an external submission" in exported.text
