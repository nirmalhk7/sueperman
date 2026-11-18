"""Guidance helps prepare evidence but never verifies it or makes declarations."""

import importlib

import pytest

from app.models import ClaimPacket


@pytest.fixture(autouse=True)
def enable_p1(monkeypatch):
    monkeypatch.setenv("P1_ENABLED", "true")


def state(client, packet):
    return client.get(f"/api/claim-packets/{packet}/obligations").raise_for_status().json()


def test_reviewed_photo_and_declaration_guidance_preserves_missing_proof(graph):
    _engine, _factory, client, _opportunity, packet, record = graph
    before = client.get(f"/api/claim-packets/{packet}").json()
    current = state(client, packet)
    assert "preparation" in current, "Source-specific preparation guidance is missing"
    assert current["preparation"]["mode"] == "guidance_only"
    assert current["preparation"]["source_url"] == record.official_url
    assert current["preparation"]["source_mode"] == "replay"
    assert current["preparation"]["optional_tips"][0]["origin"] == "organizer_tip"
    assert current["preparation"]["optional_tips"][0]["requirement"] == "optional"
    assert [item["requirement"] for item in current["items"]] == ["required", "required"]
    assert "serial" in " ".join(current["items"][0]["preparation_steps"]).lower()
    assert "does not attest" in " ".join(current["items"][1]["preparation_steps"]).lower()
    after = client.get(f"/api/claim-packets/{packet}").json()
    assert after["missing_documents"] == before["missing_documents"]
    assert after["completed_fields"] == before["completed_fields"]
    assert after["user_declaration_required"] is True


def test_unreviewed_requirement_stays_unknown_instead_of_becoming_official_instruction(graph):
    _engine, factory, client, _opportunity, packet, _record = graph
    with factory.begin() as session:
        stored = session.get(ClaimPacket, packet)
        stored.payload = stored.payload | {"required_documents": ["Unreviewed extra proof request"]}
    current = state(client, packet)
    assert current["items"][0].get("requirement") == "unknown"
    assert "not reviewed" in " ".join(current["items"][0]["preparation_steps"]).lower()


def preparation_module():
    try:
        module = importlib.import_module("app.p1.preparation")
    except ModuleNotFoundError:
        module = None
    assert callable(getattr(module, "plan", None)), "Reviewed preparation policy is not implemented"
    return module


def test_conditional_baseus_photo_is_unknown_until_condition_is_confirmed(graph):
    module = preparation_module()
    _engine, _factory, _client, _opportunity, _packet, record = graph
    documents = ["Photo showing model number and serial number",
                 "If no order number, photo showing name and date written on the charger as directed by the notice",
                 "User confirmation of lawful disposal (never prefilled)"]
    recall = record.model_copy(update={"reference": "25-248",
        "official_url": "https://www.cpsc.gov/Recalls/2025/Baseus-Portable-Chargers-Recalled-Due-to-Fire-Hazard-Sold-on-Amazon-com-by-Shenzhen-Baseus-Technology",
        "required_documents": documents})
    result = module.plan(recall, documents)
    assert [item["requirement"] for item in result["items"]] == ["required", "unknown", "required"]
    assert "order number" in " ".join(result["items"][1]["preparation_steps"]).lower()


def test_guidance_policy_change_resets_readiness_and_requires_reapproval(graph, monkeypatch):
    module = preparation_module()
    _engine, _factory, client, _opportunity, packet, _record = graph
    previous = state(client, packet)
    client.post(f"/api/claim-packets/{packet}/obligations", json={"binding": previous["binding"],
        "item_id": previous["items"][0]["id"], "ready": True, "confirmed": True}).raise_for_status()
    client.post(f"/api/claim-packets/{packet}/approve-local", json={"confirmed": True}).raise_for_status()
    monkeypatch.setattr(module, "policy_digest", lambda: "b" * 64)
    current = state(client, packet)
    assert current["binding"] != previous["binding"]
    assert all(not item["ready"] for item in current["items"])
    assert client.post(f"/api/claim-packets/{packet}/export").status_code == 409


def test_preparation_export_retains_citation_and_explicit_guidance_limit(graph):
    _engine, _factory, client, _opportunity, packet, record = graph
    current = state(client, packet)
    client.post(f"/api/claim-packets/{packet}/obligations", json={"binding": current["binding"],
        "item_id": current["items"][0]["id"], "ready": True, "confirmed": True}).raise_for_status()
    client.post(f"/api/claim-packets/{packet}/approve-local", json={"confirmed": True}).raise_for_status()
    text = client.post(f"/api/claim-packets/{packet}/export").raise_for_status().text
    assert "Preparation guidance" in text
    assert "Optional organizer tip" in text
    assert "No evidence files are collected or verified by this checklist" in text
    assert record.official_url in text
    assert "Missing evidence" in text


def test_guidance_is_exported_even_when_no_readiness_was_reported(graph):
    _engine, factory, client, _opportunity, packet, _record = graph
    from app.p1.obligations import ObligationState

    client.post(f"/api/claim-packets/{packet}/approve-local", json={"confirmed": True}).raise_for_status()
    text = client.post(f"/api/claim-packets/{packet}/export").raise_for_status().text
    assert "Preparation guidance" in text
    assert "Optional organizer tip" in text
    assert "Evidence readiness — self-reported, not verified" not in text
    with factory() as session:
        assert session.query(ObligationState).count() == 0


def test_known_label_at_an_unreviewed_source_does_not_inherit_reviewed_instructions(graph):
    module = preparation_module()
    _engine, _factory, _client, _opportunity, _packet, record = graph
    changed = record.model_copy(update={"official_url": "https://www.cpsc.gov/Recalls/2026/Unknown-Notice"})
    result = module.plan(changed, record.required_documents)
    assert all(item["requirement"] == "unknown" for item in result["items"])


@pytest.mark.parametrize("status", ["approved_local", "exported"])
def test_legacy_approval_cannot_export_new_guidance_until_fresh_approval(graph, status):
    _engine, factory, client, _opportunity, packet, _record = graph
    with factory.begin() as session:
        stored = session.get(ClaimPacket, packet)
        stored.payload = stored.payload | {"status": status, "p1_approval_binding": None}
    assert client.post(f"/api/claim-packets/{packet}/export").status_code == 409
    current = client.get(f"/api/claim-packets/{packet}").json()
    assert current["status"] == "ready_for_review"
    assert current["approved_at"] is None
    client.post(f"/api/claim-packets/{packet}/approve-local", json={"confirmed": True}).raise_for_status()
    exported = client.post(f"/api/claim-packets/{packet}/export").raise_for_status()
    assert "Preparation guidance" in exported.text
