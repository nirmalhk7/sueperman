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


def test_failed_primary_source_refresh_invalidates_prior_local_approval(tmp_path, monkeypatch):
    from app.main import create_app
    from app.providers.settlement import DOCUMENTS, HOME, NOTICE, ORDER

    monkeypatch.setenv("SETTLEMENT_LIVE_ENABLED", "true")
    with respx.mock as routes:
        for url, file in [
            (HOME, "home.html"),
            (DOCUMENTS, "documents.html"),
            (NOTICE, "notice.pdf"),
            (ORDER, "order.pdf"),
        ]:
            routes.get(url).respond(200, content=(FIXTURES / file).read_bytes())
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/refresh.db")) as client:
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
            first = client.post(
                "/api/runs",
                json={"purchase_ids": imported["purchase_ids"], "mode": "live", "idempotency_key": "first"},
            ).json()
            case = client.get("/api/opportunities", params={"run_id": first["run_id"]}).json()[0]
            packet = client.post(f"/api/opportunities/{case['id']}/claim-packet").json()
            assert (
                client.post(
                    f"/api/claim-packets/{packet['id']}/approve-local", json={"confirmed": True}
                ).status_code
                == 200
            )
            routes.get(NOTICE).respond(
                200, content=(FIXTURES / "notice.pdf").read_bytes() + b"\n% changed official source\n"
            )
            client.post(
                "/api/runs",
                json={"purchase_ids": imported["purchase_ids"], "mode": "live", "idempotency_key": "changed"},
            )
            assert client.post(f"/api/claim-packets/{packet['id']}/export").status_code == 409
            assert client.post(f"/api/opportunities/{case['id']}/claim-packet").status_code == 409
            detail = client.get(f"/api/opportunities/{case['id']}").json()
            assert detail["status"] == "unavailable"
            assert detail["sources_verified"] is False
            assert client.get(f"/api/claim-packets/{packet['id']}").json()["approved_at"] is None

            events = client.get(f"/api/runs/{first['run_id']}/events").json()
            assert events[-1]["stage"] == "COMPLETED"

            routes.get(NOTICE).respond(200, content=(FIXTURES / "notice.pdf").read_bytes())
            client.post(
                "/api/runs",
                json={
                    "purchase_ids": imported["purchase_ids"],
                    "mode": "live",
                    "idempotency_key": "restored",
                },
            )
            restored = client.get(f"/api/opportunities/{case['id']}").json()
            assert restored["status"] == "uncertain" and restored["sources_verified"] is True
            fresh = client.get(f"/api/claim-packets/{packet['id']}").json()
            assert fresh["status"] == "ready_for_review" and fresh["approved_at"] is None
            assert client.post(f"/api/claim-packets/{packet['id']}/export").status_code == 409
