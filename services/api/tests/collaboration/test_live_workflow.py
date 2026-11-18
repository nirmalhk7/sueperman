"""Real-purchase case lifecycle with controlled vendor boundaries, no paid calls."""

import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def live_client(tmp_path, monkeypatch):
    try:
        from app.collaboration import live
    except ImportError:
        pytest.fail("Live team workflow is not implemented")
    for key, value in {
        "COLLABORATION_LIVE_ENABLED": "true", "AGENT37_API_KEY": "key",
        "LYZR_API_KEY": "key", "LYZR_REVIEW_AGENT_ID": "reviewer", "LYZR_AGENT_ID": "builder",
        "LYZR_USER_ID": "user", "BAND_ROOM_ID": "room",
        **{f"BAND_{role}_{field}": f"{role}-{field}" for role in ("CONTROLLER", "SCOUT", "SKEPTIC", "BUILDER")
           for field in ("AGENT_ID", "API_KEY")},
    }.items():
        monkeypatch.setenv(key, value)

    class HttpBoundaryTransport:
        def __init__(self, credentials, handlers):
            self.handlers, self.receipts = handlers, []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def exchange(self, task, binding):
            self.receipts.append({"provider": "band", "role": task.recipient, "request_id": task.task_id})
            return await self.handlers[{"scout": "researcher", "skeptic": "skeptic", "builder": "builder"}[task.recipient]](task)

    monkeypatch.setattr(live, "LiveTransport", HttpBoundaryTransport)
    rows = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    from app.collaboration.live_providers import PUBLIC_WORKER_SHA256

    def inference(request):
        body = json.loads(request.content)
        message = json.loads(body["message"])
        if body["agent_id"] == "reviewer":
            output = {"review_note": "Compare the exact model with the supplied official notice.",
                "requested_fields": [], "evidence_refs": message["task"]["source_refs"], "uncertainty": False}
        else:
            task = message["task"]
            output = {"schema_version": 1, "task_id": task["task_id"], "case_id": task["case_id"],
                "revision": task["revision"], "provider": "lyzr", "mode": "live",
                "provider_ref": None, "duration_ms": 0, **message["validated_review"]}
        assert "Private Shop" not in body["message"]
        return httpx.Response(200, json={"response": json.dumps(output)})

    with respx.mock(assert_all_called=False) as router:
        router.post("https://api.agent37.com/v1/instances").respond(201, json={"id": "owned", "status": "running"})
        execution = router.post("https://sandbox.agent37.app/v1/instances/owned/exec").respond(200,
            json={"exit_code": 0, "truncated": False, "stderr": "", "stdout": json.dumps({
                "rows": rows, "worker_sha256": PUBLIC_WORKER_SHA256})})
        router.delete("https://api.agent37.com/v1/instances/owned").respond(200, json={"id": "owned", "deleted": True})
        router.post("https://agent-prod.studio.lyzr.ai/v3/inference/chat/").mock(side_effect=inference)
        source = router.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=rows)
        with TestClient(create_app(f"sqlite:///{tmp_path}/live.db")) as client:
            yield client, execution, source


def start(client, model="ZHX-PB22"):
    result = client.post("/api/uploads/purchases", files={"file": ("purchase.csv",
        ("order_id,purchased_at,merchant,product_name,brand,model_number\n"
         f"{model or 'missing'},2024-06-12,Private Shop,Portable Power Bank,NEWDERY,{model}\n").encode(), "text/csv")})
    product_id = result.json()["product_ids"][0]
    response = client.post("/api/collaborations", json={"product_ids": [product_id], "mode": "live",
        "idempotency_key": model or "missing"})
    assert response.status_code == 200, response.text
    return client.get(f"/api/collaborations/{response.json()['id']}").json()


def test_live_exact_case_persists_three_roles_and_exports_only_after_approval(live_client):
    client, _, _ = live_client
    run = start(client)
    assert run["status"] == "ready_for_review", run
    assert run["mode"] == "live"
    assert run["evidence"][0]["mode"] == "live"
    assert run["board"]["decision"] == "verified_match"
    events = client.get(f"/api/collaborations/{run['id']}/events").json()
    assert [(e["sender"], e["provider"]) for e in events if e["kind"] == "result"] == [
        ("scout", "agent37"), ("skeptic", "lyzr"), ("builder", "lyzr")]
    assert client.post(f"/api/collaborations/{run['id']}/export").status_code == 409
    assert client.post(f"/api/collaborations/{run['id']}/approve-local", json={"confirmed": True}).status_code == 200
    exported = client.post(f"/api/collaborations/{run['id']}/export")
    assert exported.status_code == 200
    assert "ZHX-PB22" in exported.text and "OFFLINE REPLAY" not in exported.text
    assert "not an external submission" in exported.text


@pytest.mark.parametrize("model,status", [("ZHX-PB23", "rejected"), ("", "needs_information")])
def test_live_exclusion_and_missing_fact_never_grant_export(live_client, model, status):
    client, _, _ = live_client
    run = start(client, model)
    assert run["status"] == status
    assert client.post(f"/api/collaborations/{run['id']}/export").status_code == 409
    if not model:
        assert run["board"]["question_field"] == "model_number"


def test_live_scout_failure_is_partial_without_a_recorded_match(live_client):
    client, execution, _ = live_client
    execution.respond(503)
    run = start(client)
    assert run["status"] == "partial"
    assert run["evidence"] == []
    assert run["live_sponsor_proof"] == []


def test_changed_official_evidence_revokes_live_case_export(live_client):
    client, _, source = live_client
    run = start(client)
    endpoint = f"/api/collaborations/{run['id']}"
    assert client.post(endpoint + "/approve-local", json={"confirmed": True}).status_code == 200
    rows = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    rows[0]["Description"] += " Only serial OTHER is included."
    source.respond(200, json=rows)
    assert client.post(endpoint + "/export").status_code == 409


def test_live_answer_opens_new_revision_with_confirmed_fact(live_client):
    client, _, _ = live_client
    initial = start(client, "")
    response = client.post(f"/api/collaborations/{initial['id']}/answers", json={
        "revision": initial["revision"], "field": "model_number", "value": "ZHX-PB22",
        "confirmed": True, "idempotency_key": "confirmed-model"})
    assert response.status_code == 200, response.text
    run = client.get(f"/api/collaborations/{response.json()['id']}").json()
    assert run["status"] == "ready_for_review"
    assert run["revision"] > initial["revision"]
    assert client.post(f"/api/collaborations/{initial['id']}/claim-packet").status_code == 409
