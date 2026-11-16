"""Synthetic-only V2 behavioral acceptance; no sponsor credentials or traffic."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/v2.db")) as c:
        yield c


def start(c, index=0, **kwargs):
    products = c.post("/api/demo/reset").json()["product_ids"]
    body = {"product_ids": [products[index]], "idempotency_key": "case", "mode": "replay"} | kwargs
    response = c.post("/api/collaborations", json=body)
    assert response.status_code == 200, response.text
    return response.json(), body


@pytest.mark.parametrize("index,state", [(0, "ready_for_review"), (1, "rejected"), (3, "needs_information")])
def test_three_roles_change_board_and_preserve_deterministic_decision(client, index, state):
    case, body = start(client, index)
    case = client.get(f"/api/collaborations/{case['id']}").json()
    assert case["status"] == state
    assert case["mode"] == "replay"
    assert case["live_sponsor_proof"] is False
    assert list(case["board"]) == ["finding", "challenge", "missing_information", "decision", "evidence"]
    events = client.get(f"/api/collaborations/{case['id']}/events").json()
    assert [e["recipient"] for e in events if e["kind"] == "request"] == ["scout", "skeptic", "builder"]
    assert all(e["mode"] == "replay" for e in events)
    assert all(e["source_refs"] for e in events if e["kind"] == "result")
    assert len(events) == 6
    assert client.post("/api/collaborations", json=body).json()["id"] == case["id"]
    assert len(client.get(f"/api/collaborations/{case['id']}/events").json()) == 6
    if state == "rejected":
        assert "model_number" in case["board"]["challenge"]
        assert (
            client.post(
                f"/api/collaborations/{case['id']}/approve-local",
                json={"revision": case["revision"], "confirmed": True},
            ).status_code
            == 409
        )
    if state == "needs_information":
        assert case["question"]["field"] == "model_number"


def test_answer_is_explicit_revision_bound_and_does_not_edit_v1(client):
    case, body = start(client, 3)
    case = client.get(f"/api/collaborations/{case['id']}").json()
    url = f"/api/collaborations/{case['id']}"
    answer = {"revision": case["revision"], "field": "model_number", "value": "ZHX-PB22", "confirmed": True}
    assert client.post(url + "/answers", json=answer | {"field": "merchant"}).status_code == 422
    assert client.post(url + "/answers", json=answer | {"confirmed": False}).status_code == 422
    response = client.post(url + "/answers", json=answer)
    assert response.status_code == 200, response.text
    revised = client.get(url).json()
    assert revised["revision"] != case["revision"]
    assert revised["status"] == "ready_for_review"
    assert len(revised["history"]) == 2
    assert client.post(url + "/answers", json=answer).status_code == 409
    products = client.get("/api/products").json()
    assert next(p for p in products if p["id"] == body["product_ids"][0])["product"]["model_number"] is None
    assert client.post(url + "/export", json={"revision": revised["revision"]}).status_code == 409
    assert (
        client.post(
            url + "/approve-local", json={"revision": revised["revision"], "confirmed": True}
        ).status_code
        == 200
    )
    exported = client.post(url + "/export", json={"revision": revised["revision"]})
    assert exported.status_code == 200
    assert "not an external submission" in exported.text
    assert "OFFLINE REPLAY" in exported.text
    assert client.post(url + "/export", json={"revision": case["revision"]}).status_code == 409


def test_live_unavailable_never_fakes_sponsor_success(client):
    case, _ = start(client, mode="live")
    case = client.get(f"/api/collaborations/{case['id']}").json()
    assert case["status"] == "partial"
    assert case["live_sponsor_proof"] is False
    assert set(case["blocked_providers"]) == {"band", "agent37", "adal", "finch", "lyzr"}
    assert case["packet"] is None


def test_idempotency_input_conflict_and_unknown_fields(client):
    _case, body = start(client)
    assert client.post("/api/collaborations", json=body | {"mode": "live"}).status_code == 409
    assert client.post("/api/collaborations", json=body | {"shell": "whoami"}).status_code == 422
    assert client.post("/api/collaborations", json=body | {"product_ids": ["unknown"]}).status_code == 409
