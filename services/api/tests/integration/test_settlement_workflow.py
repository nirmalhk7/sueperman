"""Catch missing real-case persistence, approval bypass and stale-deadline export."""

from pathlib import Path

import respx
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parents[1] / "fixtures/settlement"


def test_live_verified_case_prepares_uncertain_draft_and_exports_locally(tmp_path, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("SETTLEMENT_LIVE_ENABLED", "true")
    from app.providers.settlement import DOCUMENTS, HOME, NOTICE, ORDER

    with respx.mock as routes:
        for url, file in [
            (HOME, "home.html"),
            (DOCUMENTS, "documents.html"),
            (NOTICE, "notice.pdf"),
            (ORDER, "order.pdf"),
        ]:
            routes.get(url).respond(200, content=(FIXTURES / file).read_bytes())
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/case.db")) as client:
            imported = client.post(
                "/api/uploads/purchases",
                files={
                    "file": (
                        "purchase.csv",
                        b"product_name,merchant,purchased_at\nPrescription drug,Kroger,2024-06-12\n",
                        "text/csv",
                    )
                },
            ).json()
            run = client.post(
                "/api/runs",
                json={"purchase_ids": imported["purchase_ids"], "mode": "live", "idempotency_key": "case"},
            ).json()
            opportunities = client.get("/api/opportunities", params={"run_id": run["run_id"]}).json()
            assert len(opportunities) == 1
            case = opportunities[0]
            assert case["kind"] == "settlement" and not case["simulated"]
            assert case["status"] == "uncertain"
            detail = client.get(f"/api/opportunities/{case['id']}").json()
            assert detail["assessment"]["missing_fields"]
            assert len(detail["evidence"]) == 4
            packet = client.post(f"/api/opportunities/{case['id']}/claim-packet")
            assert packet.status_code == 200
            pid = packet.json()["id"]
            assert client.post(f"/api/claim-packets/{pid}/export").status_code == 409
            assert (
                client.post(f"/api/claim-packets/{pid}/approve-local", json={"confirmed": True}).status_code
                == 200
            )
            exported = client.post(f"/api/claim-packets/{pid}/export")
            assert exported.status_code == 200
            assert "eligibility is unconfirmed" in exported.text
            assert "Kroger" in exported.text
            assert "not an external submission" in exported.text
