"""Readiness is explicit local bookkeeping, never proof or an eligibility override."""

import copy

import pytest
from sqlalchemy import select

from app.models import ClaimPacket, Opportunity, Product, SourceEvidence


@pytest.fixture(autouse=True)
def enable_p1(monkeypatch):
    monkeypatch.setenv("P1_ENABLED", "true")


def checklist(client, packet_id):
    response = client.get(f"/api/claim-packets/{packet_id}/obligations")
    assert response.status_code == 200, response.text
    return response.json()


def update(client, packet_id, state, *, ready=True, **extra):
    return client.post(f"/api/claim-packets/{packet_id}/obligations", json={
        "binding": state["binding"], "item_id": state["items"][0]["id"],
        "ready": ready, "confirmed": True, **extra})


def test_readiness_requires_confirmation_without_changing_facts_or_missing_proof(graph):
    _engine, factory, client, opportunity_id, packet_id, _record = graph
    before = client.get(f"/api/claim-packets/{packet_id}").json()
    state = checklist(client, packet_id)
    assert state["mode"] == "self_reported"
    assert all(item["ready"] is False for item in state["items"])
    assert [item["label"] for item in state["items"]] == before["required_documents"]
    assert update(client, packet_id, state, confirmed=False).status_code == 422
    assert update(client, packet_id, state, confirmed="true").status_code == 422
    assert update(client, packet_id, state, status="verified_match").status_code == 422
    changed = update(client, packet_id, state)
    assert changed.status_code == 200
    assert changed.json()["items"][0]["ready"] is True
    assert changed.json()["items"][0]["confirmed_at"]
    after = client.get(f"/api/claim-packets/{packet_id}").json()
    for field in ("completed_fields", "required_documents", "missing_documents", "user_declaration_required"):
        assert after[field] == before[field]
    with factory() as session:
        assert session.get(Opportunity, opportunity_id).payload["status"] == "verified_match"


def test_readiness_edit_revokes_approval_export_and_repeat_is_a_noop(graph):
    _engine, _factory, client, _opportunity_id, packet_id, _record = graph
    state = checklist(client, packet_id)
    assert update(client, packet_id, state).status_code == 200
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    approved = client.post(f"/api/claim-packets/{packet_id}/approve-local", json={"confirmed": True})
    assert approved.status_code == 200
    assert update(client, packet_id, state).status_code == 200
    assert client.get(f"/api/claim-packets/{packet_id}").json()["approved_at"] == approved.json()["approved_at"]
    exported = client.post(f"/api/claim-packets/{packet_id}/export")
    assert exported.status_code == 200
    assert "Evidence readiness — self-reported, not verified" in exported.text
    assert "[x] Ready locally:" in exported.text
    assert "No declaration or submission is recorded" in exported.text
    assert update(client, packet_id, state, ready=False).status_code == 200
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409


@pytest.mark.parametrize("change", ["product", "evidence", "policy"])
def test_changed_binding_resets_readiness_rejects_stale_updates_and_revokes_export(graph, monkeypatch, change):
    _engine, factory, client, opportunity_id, packet_id, _record = graph
    state = checklist(client, packet_id)
    assert update(client, packet_id, state).status_code == 200
    assert client.post(f"/api/claim-packets/{packet_id}/approve-local", json={"confirmed": True}).status_code == 200
    if change == "policy":
        from app.p1 import obligations
        monkeypatch.setattr(obligations, "policy_digest", lambda: "b" * 64)
    else:
        with factory.begin() as session:
            opportunity = session.get(Opportunity, opportunity_id)
            if change == "product":
                product = session.get(Product, opportunity.product_id)
                payload = copy.deepcopy(product.payload)
                payload["product"]["model_number"] = "ZHX-PB23"
                product.payload = payload
            else:
                evidence = session.scalar(select(SourceEvidence).where(SourceEvidence.opportunity_id == opportunity_id))
                evidence.payload = evidence.payload | {"quoted_excerpt": "Changed official restriction"}
    current = checklist(client, packet_id)
    assert current["binding"] != state["binding"]
    assert all(item["ready"] is False for item in current["items"])
    assert current["previous_versions"] == 1
    assert update(client, packet_id, state).status_code == 409
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    with factory() as session:
        assert session.get(ClaimPacket, packet_id).payload["approved_at"] is None


def test_unknown_item_cannot_create_invented_obligation_and_state_survives_reopen(graph):
    _engine, factory, client, _opportunity_id, packet_id, _record = graph
    state = checklist(client, packet_id)
    assert update(client, packet_id, state, item_id="f" * 64).status_code == 422
    assert update(client, packet_id, state).status_code == 200
    current = checklist(client, packet_id)
    assert current["items"][0]["ready"] is True
    from app.p1.obligations import ObligationState
    with factory() as session:
        saved = session.scalar(select(ObligationState))
        assert saved.binding == state["binding"]
        assert len(session.scalars(select(ObligationState)).all()) == 1
