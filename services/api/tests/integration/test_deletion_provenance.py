"""Metadata cleanup must not replace the provenance of retained drafts."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


def test_two_deletions_preserve_newer_independent_local_draft(tmp_path, monkeypatch):
    """Clearing an old fallback link cannot make its run the latest producer."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'default.db'}")
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    from app.db import database
    from app.deletion_lifecycle import erase_purchase, plan_purchase
    from app.main import create_app
    from app.models import AgentRun, ClaimPacket, Opportunity, Purchase

    url = f"sqlite:///{tmp_path / 'provenance.db'}"
    with TestClient(create_app(url)) as client:
        client.post("/api/demo/reset").raise_for_status()
        products = client.get("/api/products").raise_for_status().json()
        by_model = {product["product"]["model_number"]: product for product in products}
        first = by_model["DC-BOTTLE-1"]
        removed = by_model["ZHX-PB23"]
        kept = by_model["ZHX-PB22"]

        def investigate(key, purchases, fallback=None):
            body = {"mode": "demo", "collaboration_mode": "local",
                    "purchase_ids": purchases, "idempotency_key": key}
            if fallback is not None:
                body["fallback_of"] = fallback
            response = client.post("/api/runs", json=body).raise_for_status().json()
            assert client.get(f"/api/runs/{response['run_id']}").json()["status"] == "completed"
            return response["run_id"]

        original = investigate("original", [first["purchase_id"]])
        shared = investigate("shared-fallback", [removed["purchase_id"], kept["purchase_id"]], original)
        independent = investigate("newer-independent", [kept["purchase_id"]])
        engine, factory = database(url)
        try:
            with factory() as session:
                opportunity = session.scalar(select(Opportunity).where(Opportunity.product_id == kept["id"]))
                packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == opportunity.id))
                packet_id, opportunity_id = packet.id, opportunity.id
                original_case = packet.payload["diwali_case_id"]
            endpoint = f"/api/claim-packets/{packet_id}"
            approval = client.post(endpoint + "/approve-local", json={"confirmed": True}).raise_for_status().json()
            draft = client.post(endpoint + "/export").raise_for_status().text

            # Both calls represent separate, explicit deletion decisions. The
            # first one only clears a retained run's fallback metadata.
            with factory.begin() as session:
                erase_purchase(session, plan_purchase(session, first["purchase_id"]))
            with factory() as session:
                assert session.get(AgentRun, original) is None
                assert session.get(AgentRun, shared).payload["fallback_of"] is None
            with factory.begin() as session:
                plan = plan_purchase(session, removed["purchase_id"])
                assert plan.public()["shared_investigations"] == 1
                erase_purchase(session, plan)

            with factory() as session:
                assert session.get(Purchase, removed["purchase_id"]) is None
                assert session.get(AgentRun, shared) is None
                assert session.get(AgentRun, independent) is not None
                assert session.get(Purchase, kept["purchase_id"]) is not None
                assert not session.get(Opportunity, opportunity_id).payload.get("stale", False)
                packet = session.get(ClaimPacket, packet_id)
                assert packet.payload["diwali_case_id"] == original_case
                assert datetime.fromisoformat(packet.payload["approved_at"]) == datetime.fromisoformat(approval["approved_at"])
            assert client.post(endpoint + "/export").raise_for_status().text == draft
        finally:
            engine.dispose()


@pytest.mark.parametrize("shared_finished,independent_finished", [
    ("2026-01-01T00:00:00Z", "2026-01-01T00:00:00.000001+00:00"),
    ("2026-01-01T01:00:00+01:00", "2026-01-01T00:30:00Z"),
])
def test_producer_order_uses_actual_instants_not_timestamp_spelling(tmp_path, shared_finished, independent_finished):
    """Both literal independent timestamps are later than the shared one."""
    from app.db import database
    from app.deletion_lifecycle import erase_purchase, plan_purchase
    from app.models import AgentRun, ClaimPacket, Opportunity, Product, Purchase

    engine, factory = database(f"sqlite:///{tmp_path / 'timestamps.db'}")
    try:
        with factory.begin() as session:
            removed = Purchase(import_key="removed", payload={})
            kept = Purchase(import_key="kept", payload={})
            session.add_all([removed, kept])
            session.flush()
            product = Product(purchase_id=kept.id, payload={})
            session.add(product)
            session.flush()
            opportunity = Opportunity(product_id=product.id, kind="recall", source_id="26-792",
                official_url="https://www.cpsc.gov/Recalls/2026/NEWDERY", payload={"status": "verified_match"})
            session.add(opportunity)
            session.flush()
            packet = ClaimPacket(opportunity_id=opportunity.id,
                payload={"status": "approved_local", "approved_at": "2026-01-01T00:35:00Z"})
            shared = AgentRun(idempotency_key="shared", status="completed",
                created_at="2025-12-31T23:59:00Z", payload={"purchase_ids": [removed.id, kept.id],
                "opportunities": [opportunity.id], "completed_at": shared_finished})
            independent = AgentRun(idempotency_key="independent", status="completed",
                created_at="2026-01-01T00:00:00Z", payload={"purchase_ids": [kept.id],
                "opportunities": [opportunity.id], "completed_at": independent_finished})
            session.add_all([packet, shared, independent])
            session.flush()
            removed_id, kept_id, opportunity_id, packet_id = removed.id, kept.id, opportunity.id, packet.id
        with factory.begin() as session:
            erase_purchase(session, plan_purchase(session, removed_id))
        with factory() as session:
            assert session.get(Purchase, removed_id) is None
            assert session.get(Purchase, kept_id) is not None
            assert not session.get(Opportunity, opportunity_id).payload.get("stale", False)
            assert session.get(ClaimPacket, packet_id).payload["approved_at"] == "2026-01-01T00:35:00Z"
    finally:
        engine.dispose()


def test_later_partial_for_another_purchase_cannot_revoke_independent_draft(tmp_path):
    """A+B partial, B success, then A+C partial must not reset B's approval."""
    from app.db import database
    from app.deletion_lifecycle import erase_purchase, plan_purchase
    from app.models import AgentRun, ClaimPacket, Opportunity, Product, Purchase

    engine, factory = database(f"sqlite:///{tmp_path / 'partial-members.db'}")
    try:
        with factory.begin() as session:
            removed = Purchase(import_key="removed", payload={})
            kept = Purchase(import_key="kept", payload={})
            unrelated = Purchase(import_key="unrelated", payload={})
            session.add_all([removed, kept, unrelated])
            session.flush()
            product = Product(purchase_id=kept.id, payload={})
            session.add(product)
            session.flush()
            opportunity = Opportunity(product_id=product.id, kind="recall", source_id="26-792",
                official_url="https://www.cpsc.gov/Recalls/2026/NEWDERY", payload={"status": "verified_match"})
            session.add(opportunity)
            session.flush()
            packet = ClaimPacket(opportunity_id=opportunity.id,
                payload={"status": "approved_local", "approved_at": "2026-01-01T00:02:30Z"})
            old_partial = AgentRun(idempotency_key="old-partial", status="partial",
                created_at="2026-01-01T00:01:00Z", payload={"purchase_ids": [removed.id, kept.id],
                "opportunities": []})
            independent = AgentRun(idempotency_key="independent", status="completed",
                created_at="2026-01-01T00:02:00Z", payload={"purchase_ids": [kept.id],
                "opportunities": [opportunity.id], "completed_at": "2026-01-01T00:02:10Z"})
            other_partial = AgentRun(idempotency_key="other-partial", status="partial",
                created_at="2026-01-01T00:03:00Z", payload={"purchase_ids": [removed.id, unrelated.id],
                "opportunities": []})
            session.add_all([packet, old_partial, independent, other_partial])
            session.flush()
            removed_id, kept_id, unrelated_id = removed.id, kept.id, unrelated.id
            opportunity_id, packet_id, independent_id = opportunity.id, packet.id, independent.id
        with factory.begin() as session:
            erase_purchase(session, plan_purchase(session, removed_id))
        with factory() as session:
            assert session.get(Purchase, removed_id) is None
            assert session.get(Purchase, kept_id) is not None
            assert session.get(Purchase, unrelated_id) is not None
            assert session.get(AgentRun, independent_id) is not None
            assert not session.get(Opportunity, opportunity_id).payload.get("stale", False)
            assert session.get(ClaimPacket, packet_id).payload["approved_at"] == "2026-01-01T00:02:30Z"
    finally:
        engine.dispose()
