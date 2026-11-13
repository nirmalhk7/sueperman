import json

import httpx
import respx
from fastapi.testclient import TestClient


def test_openai_flag_routes_live_mode_through_openai_without_changing_hard_gates(tmp_path, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-token")
    seen = []

    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"choice":"produce_packet"}'}],
                    }
                ],
            },
        )

    with respx.mock as r:
        r.post("https://api.openai.com/v1/responses").mock(side_effect=respond)
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/openai.db")) as c:
            seed = c.post("/api/demo/reset").json()
            started = c.post(
                "/api/runs",
                json={"purchase_ids": seed["purchase_ids"], "mode": "live", "idempotency_key": "openai"},
            ).json()
            run = c.get(f"/api/runs/{started['run_id']}").json()
            assert run["provider_modes"]["decision"] == "openai"
            assert len(seen) == 3
            assert run["summary"]["verified_matches"] == 1
            assert run["summary"]["rejected"] == 1
            assert run["summary"]["needs_review"] == 1
            detail = c.get("/api/opportunities", params={"run_id": started["run_id"]}).json()
            excluded = next(o for o in detail if o["status"] == "rejected")
            assessment = c.get(f"/api/opportunities/{excluded['id']}").json()["assessment"]
            assert assessment["decision_raw_summary"]["overridden"] is True
            assert assessment["performed_by"] == "openai_assisted"


def test_per_run_model_budget_preserves_all_hard_gate_results(tmp_path, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_MAX_CALLS_PER_RUN", "1")
    with respx.mock as routes:
        remote = routes.post("https://api.openai.com/v1/responses").respond(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"choice":"produce_packet"}'}],
                    }
                ],
            },
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/budget.db")) as client:
            seed = client.post("/api/demo/reset").json()
            started = client.post(
                "/api/runs",
                json={"purchase_ids": seed["purchase_ids"], "mode": "live", "idempotency_key": "budget"},
            ).json()
            run = client.get(f"/api/runs/{started['run_id']}").json()
            assert remote.call_count == 1
            assert run["summary"]["verified_matches"] == 1
            assert run["summary"]["rejected"] == 1
            assert run["summary"]["needs_review"] == 1
            assert any("budget" in warning.lower() for warning in run["warnings"])


def test_inspect_more_investigates_ambiguous_candidate_without_bypassing_missing_model(tmp_path, monkeypatch):
    from datetime import UTC, datetime
    from pathlib import Path

    from app.main import create_app
    from app.providers.brightdata import ResearchEvidence

    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("BRIGHTDATA_ENABLED", "true")
    monkeypatch.setenv("BRIGHTDATA_API_TOKEN", "test")
    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")

    async def research(self, recall):
        return ResearchEvidence(
            url=recall.contact_url,
            publisher="NEWDERY",
            fetched_at=datetime.now(UTC),
            quoted_excerpt="ZHX-PB22 refund",
            content_sha256="a" * 64,
        )

    monkeypatch.setattr("app.providers.brightdata.BrightDataResearcher.research", research)
    with respx.mock as routes:
        raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
        routes.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=raw)
        routes.post("https://api.openai.com/v1/responses").respond(
            200,
            json={
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"choice":"inspect_more"}'}],
                    }
                ],
            },
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/inspect.db")) as client:
            imported = client.post(
                "/api/uploads/purchases",
                files={"file": ("purchase.csv", b"product_name,brand\nPower Bank,NEWDERY\n", "text/csv")},
            ).json()
            started = client.post(
                "/api/runs",
                json={"purchase_ids": imported["purchase_ids"], "mode": "live", "idempotency_key": "inspect"},
            ).json()
            items = client.get("/api/opportunities", params={"run_id": started["run_id"]}).json()
            assert len(items) == 1
            detail = client.get(f"/api/opportunities/{items[0]['id']}").json()
            assert detail["status"] == "needs_review"
            assert any(e["source_type"] == "manufacturer" for e in detail["evidence"])
            assert client.post(f"/api/opportunities/{items[0]['id']}/claim-packet").status_code == 409
            events = client.get(f"/api/runs/{started['run_id']}/events").json()
            assert any(
                e["stage"] == "INVESTIGATION_ROUTED" and e["outcome"] == "inspect_more" for e in events
            )
