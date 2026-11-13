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
