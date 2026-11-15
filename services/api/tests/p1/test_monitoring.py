"""Persistent source watches must revoke stale approval, never replay paid work."""

import asyncio
from datetime import timedelta

import pytest
from monitor_helpers import NOW, enable, monitor
from sqlalchemy import select

from app.models import AgentRun, ClaimPacket, Opportunity, Product


@pytest.mark.asyncio
async def test_unchanged_timestamp_only_refresh_preserves_approval_and_daily_schedule(graph):
    module = monitor()
    engine, factory, client, opportunity_id, packet_id, record = graph
    watch_id = enable(module, engine, factory, opportunity_id)
    calls = []
    async def checker(reference):
        calls.append(reference)
        # A different connection can write: no coordinator transaction spans the await.
        with engine.begin() as conn:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        return record.model_copy(update={"fetched_at": NOW})
    result = await module.check_due(factory, checker, clock=lambda: NOW)
    assert result == ["unchanged"]
    assert await module.check_due(factory, checker, clock=lambda: NOW + timedelta(hours=23)) == []
    assert calls == ["26-792"]
    with factory.begin() as s:
        # An idempotent enable cannot turn a daily watch into repeated immediate reads.
        module.set_watch(s, opportunity_id, enabled=True, observed_at=NOW + timedelta(hours=12))
    with factory() as s:
        watch = s.get(module.SourceWatch, watch_id)
        assert watch.due_at == (NOW + timedelta(hours=24)).isoformat()
        assert s.scalar(select(module.SourceCheck)).payload["status"] == "unchanged"
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 200


@pytest.mark.asyncio
async def test_inflight_disable_cannot_be_reenabled_into_a_stale_result(graph):
    module = monitor()
    engine, factory, _client, opportunity_id, _packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    async def checker(reference):
        with factory.begin() as s:
            module.set_watch(s, opportunity_id, enabled=False, observed_at=NOW)
            with pytest.raises(ValueError, match="in-flight"):
                module.set_watch(s, opportunity_id, enabled=True, observed_at=NOW)
        return record
    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["stale"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [False, True])
async def test_new_investigation_cannot_preserve_old_approval_after_changed_or_failed_check(graph, failure):
    module = monitor()
    engine, factory, client, opportunity_id, packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    async def checker(reference):
        with factory.begin() as session:
            session.add(AgentRun(idempotency_key="started-during-check", status="running", payload={}))
        if failure:
            raise RuntimeError("injected source outage")
        return record.model_copy(update={"models": ["ZHX-PB23"]})
    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["stale"]
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    with factory() as session:
        assert session.get(Opportunity, opportunity_id).payload["recall"] == record.model_dump(mode="json")
        check = session.scalar(select(module.SourceCheck))
        assert check.payload["observation_status"] == ("unavailable" if failure else "changed")


@pytest.mark.asyncio
async def test_changed_source_revokes_export_and_retains_both_snapshots(graph):
    module = monitor()
    engine, factory, client, opportunity_id, packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    changed = record.model_copy(update={"models": ["ZHX-PB23"], "fetched_at": NOW})
    async def checker(reference):
        return changed
    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["changed"]
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    assert client.post(f"/api/claim-packets/{packet_id}/approve-local", json={"confirmed": True}).status_code == 409
    detail = client.get(f"/api/opportunities/{opportunity_id}").json()
    assert detail["assessment"]["outcome"] == "uncertain"
    assert any(c["name"] == "unsupported_source_conditions" and c["status"] == "unknown"
               for c in detail["assessment"]["hard_conditions"])
    assert "decision_raw_summary" not in detail["assessment"]
    with factory() as s:
        check = s.scalar(select(module.SourceCheck))
        assert check.payload["before"]["models"] == ["ZHX-PB22"]
        assert check.payload["after"]["models"] == ["ZHX-PB23"]
        assert s.get(ClaimPacket, packet_id).payload["approved_at"] is None
        assert s.get(Opportunity, opportunity_id).payload["status"] == "needs_review"


@pytest.mark.asyncio
async def test_timeout_revokes_approval_without_automatic_retry_or_recovery_approval(graph):
    module = monitor()
    engine, factory, client, opportunity_id, packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    calls = []
    async def blocked(reference):
        calls.append(reference)
        await asyncio.sleep(100)
    assert await module.check_due(factory, blocked, clock=lambda: NOW, timeout_seconds=0.01) == ["unavailable"]
    assert await module.check_due(factory, blocked, clock=lambda: NOW) == []
    assert calls == ["26-792"]
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409
    async def recovered(reference):
        return record
    assert await module.check_due(factory, recovered, clock=lambda: NOW + timedelta(days=1)) == ["unchanged"]
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409


@pytest.mark.asyncio
async def test_concurrent_ticks_read_once_and_skip_active_runs(graph):
    module = monitor()
    engine, factory, _client, opportunity_id, _packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    calls = []
    async def checker(reference):
        calls.append(reference)
        await asyncio.sleep(0.01)
        return record
    results = await asyncio.gather(*(module.check_due(factory, checker, clock=lambda: NOW) for _ in range(2)))
    assert sorted(results, key=len) == [[], ["unchanged"]]
    assert calls == ["26-792"]
    with factory.begin() as s:
        s.add(AgentRun(idempotency_key="active", status="running", payload={}))
    assert await module.check_due(factory, checker, clock=lambda: NOW + timedelta(days=1)) == []
    assert calls == ["26-792"]


def test_restart_disables_inflight_watch_and_migration_preserves_legacy_rows(graph):
    module = monitor()
    engine, factory, client, opportunity_id, packet_id, _record = graph
    with factory() as s:
        before = [(p.id, p.payload) for p in s.scalars(select(Product))]
    watch_id = enable(module, engine, factory, opportunity_id)
    module.setup_schema(engine)
    with factory.begin() as s:
        row = s.get(module.SourceWatch, watch_id)
        row.status = "checking"
        module.recover_interrupted(s, NOW)
    with factory() as s:
        assert [(p.id, p.payload) for p in s.scalars(select(Product))] == before
        row = s.get(module.SourceWatch, watch_id)
        assert row.status == "interrupted" and row.enabled is False
    assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 409


@pytest.mark.asyncio
async def test_wrong_source_cannot_replace_current_snapshot(graph):
    module = monitor()
    engine, factory, _client, opportunity_id, _packet_id, record = graph
    enable(module, engine, factory, opportunity_id)
    async def checker(reference):
        return record.model_copy(update={"reference": "99-999", "official_url": "https://evil.example/Recalls/x"})
    assert await module.check_due(factory, checker, clock=lambda: NOW) == ["unavailable"]
    with factory() as s:
        assert s.get(Opportunity, opportunity_id).payload["recall"] == record.model_dump(mode="json")


def test_at_most_five_active_watches_and_existing_watch_can_be_disabled(graph):
    module = monitor()
    engine, factory, _client, opportunity_id, _packet_id, _record = graph
    module.setup_schema(engine)
    with factory.begin() as s:
        original = s.get(Opportunity, opportunity_id)
        product = s.get(Product, original.product_id)
        ids = []
        for _ in range(6):
            clone = Product(purchase_id=product.purchase_id, payload=product.payload, demo=True)
            s.add(clone)
            s.flush()
            opportunity = Opportunity(product_id=clone.id, kind="recall", source_id=original.source_id,
                official_url=original.official_url, payload=original.payload, demo=True)
            s.add(opportunity)
            s.flush()
            ids.append(opportunity.id)
        for identifier in ids[:5]:
            module.set_watch(s, identifier, enabled=True, observed_at=NOW)
        with pytest.raises(ValueError, match="Five"):
            module.set_watch(s, ids[5], enabled=True, observed_at=NOW)
        module.set_watch(s, ids[0], enabled=False, observed_at=NOW)
        assert module.set_watch(s, ids[5], enabled=True, observed_at=NOW).enabled
