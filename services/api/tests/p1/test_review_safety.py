"""Real SQLite regressions for replay bypass and monitor/approval serialization."""

import pytest
from monitor_helpers import NOW, enable, monitor
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.models import AuditEvent, ClaimPacket, Opportunity, Product, Purchase


@pytest.fixture(autouse=True)
def enabled(monkeypatch):
    monkeypatch.setenv("P1_ENABLED", "true")
    monkeypatch.setenv("DIWALI_ENABLED", "true")


@pytest.mark.parametrize("transport", ["deterministic", "local"])
@pytest.mark.parametrize("outage", [False, True])
async def test_recorded_rerun_cannot_erase_official_monitor_revocation(graph, transport, outage):
    engine, factory, client, opportunity_id, packet_id, record = graph
    module = monitor()
    enable(module, engine, factory, opportunity_id)

    async def checker(reference):
        if outage:
            raise RuntimeError("synthetic outage")
        return record.model_copy(update={"models": ["ZHX-PB23"], "fetched_at": NOW})

    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["unavailable" if outage else "changed"]
    with factory() as session:
        product = session.get(Product, session.get(Opportunity, opportunity_id).product_id)
        purchase = session.get(Purchase, product.purchase_id)
        purchase_id = purchase.id
    rerun = client.post("/api/runs", json={"purchase_ids": [purchase_id], "mode": "demo",
        "collaboration_mode": transport, "idempotency_key": f"replay-{transport}-{outage}"})
    assert rerun.status_code == 200, rerun.text
    if transport == "deterministic":
        with factory() as session:
            events = session.scalars(select(AuditEvent).where(AuditEvent.run_id == rerun.json()["run_id"])).all()
            assert [e.payload["outcome"] for e in events
                    if e.payload["stage"] == "ELIGIBILITY_EVALUATED"] == ["needs_review"]
            assert not any(e.payload["stage"] == "PACKET_PREPARED" for e in events)
    assert client.post(f"/api/claim-packets/{packet_id}/approve-local", json={"confirmed": True}).status_code == 409
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    with factory() as session:
        opportunity = session.get(Opportunity, opportunity_id)
        assert opportunity.payload["status"] == "needs_review"
        assert opportunity.payload["recall"]["models"] == (["ZHX-PB22"] if outage else ["ZHX-PB23"])
        assert session.get(ClaimPacket, packet_id).payload["approved_at"] is None


@pytest.mark.parametrize("action", ["approve-local", "export"])
def test_approval_and_export_serialize_with_monitor_revocation(graph, monkeypatch, action):
    engine, factory, client, opportunity_id, packet_id, _record = graph
    module = monitor()
    enable(module, engine, factory, opportunity_id)
    from app.api import claims
    original = claims.draft_allowed
    blocked = []

    def concurrent_revoke(opportunity):
        # At the final eligibility gate, an independent writer must not be able
        # to commit a revocation that this stale request then overwrites.
        with factory() as other:
            other.connection().exec_driver_sql("PRAGMA busy_timeout=0")
            try:
                other.connection().exec_driver_sql("BEGIN IMMEDIATE")
            except OperationalError as error:
                assert "locked" in str(error)
                blocked.append(True)
            else:
                module.revoke(other, other.get(Opportunity, opportunity_id), "SOURCE_MONITOR_UNAVAILABLE", NOW)
                other.commit()
                blocked.append(False)
        return original(opportunity)

    monkeypatch.setattr(claims, "draft_allowed", concurrent_revoke)
    response = client.post(f"/api/claim-packets/{packet_id}/{action}", json={"confirmed": True})
    assert response.status_code == 200, response.text
    assert blocked == [True]
    monkeypatch.setattr(claims, "draft_allowed", original)
    with factory.begin() as session:
        module.revoke(session, session.get(Opportunity, opportunity_id), "SOURCE_MONITOR_UNAVAILABLE", NOW)
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    with factory() as session:
        packet = session.scalar(select(ClaimPacket).where(ClaimPacket.id == packet_id))
        assert packet.payload["status"] == "needs_evidence"
        assert packet.payload["approved_at"] is None


async def test_durable_check_blocks_rebuilt_rows_but_allows_later_live_review(graph):
    from datetime import timedelta

    from app.p1.monitoring import review_required
    engine, factory, client, opportunity_id, packet_id, record = graph
    module = monitor()
    watch_id = enable(module, engine, factory, opportunity_id)

    async def checker(reference):
        raise RuntimeError("synthetic outage")

    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["unavailable"]
    with factory.begin() as session:
        # Compatibility with histories written before review_required_at existed.
        watch = session.get(module.SourceWatch, watch_id)
        watch.payload = {k: v for k, v in watch.payload.items() if k != "review_required_at"}
        opportunity = session.get(Opportunity, opportunity_id)
        opportunity.payload = opportunity.payload | {"status": "verified_match", "monitor_status": None}
        packet = session.get(ClaimPacket, packet_id)
        packet.payload = packet.payload | {"status": "approved_local", "approved_at": NOW.isoformat()}
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    with factory() as session:
        opportunity = session.get(Opportunity, opportunity_id)
        assert review_required(session, opportunity, record.model_copy(update={
            "mode": "live", "fetched_at": NOW}))
        assert review_required(session, opportunity, record.model_copy(update={
            "fetched_at": NOW + timedelta(minutes=1)}))
        assert not review_required(session, opportunity, record.model_copy(update={
            "mode": "live", "fetched_at": NOW + timedelta(minutes=1)}))


async def test_new_replay_case_board_cannot_approve_a_monitored_withdrawn_source(graph):
    engine, factory, client, opportunity_id, _packet_id, record = graph
    module = monitor()
    enable(module, engine, factory, opportunity_id)

    async def checker(reference):
        return record.model_copy(update={"models": ["ZHX-PB23"], "fetched_at": NOW})

    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["changed"]
    with factory() as session:
        product_id = session.get(Opportunity, opportunity_id).product_id
    started = client.post("/api/collaborations", json={"product_ids": [product_id],
        "mode": "replay", "idempotency_key": "withdrawn-source-new-case"})
    assert started.status_code == 200, started.text
    identifier = started.json()["id"]
    assert client.post(f"/api/collaborations/{identifier}/claim-packet").status_code == 409
    assert client.post(f"/api/collaborations/{identifier}/approve-local", json={"confirmed": True}).status_code == 409
    assert client.post(f"/api/collaborations/{identifier}/export").status_code == 409
