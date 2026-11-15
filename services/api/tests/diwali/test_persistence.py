"""Coordinator atomicity protects V1 rows, drafts and interrupted tasks."""

import importlib
from dataclasses import replace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_local_core import fixture_data, inputs

from app.db import database
from app.models import AgentRun, ClaimPacket, Opportunity, Product, Purchase


def persistence():
    try:
        return importlib.import_module("app.diwali.persistence")
    except ModuleNotFoundError:
        pytest.fail("V2.1 transaction facade is not implemented")


def setup(tmp_path):
    module = persistence()
    engine, factory = database(f"sqlite:///{tmp_path}/atomic.db")
    module.setup_schema(engine)
    products, recall = fixture_data()
    with factory.begin() as session:
        purchase = Purchase(import_key="synthetic", demo=True, payload={})
        session.add(purchase)
        session.flush()
        product = Product(purchase_id=purchase.id, demo=True, model_number="ZHX-PB22",
                          payload={"product": products[0].model_dump(mode="json")})
        run = AgentRun(idempotency_key="local", demo=True, status="running", payload={
            "collaboration_mode": "local", "purchase_ids": [purchase.id],
            "opportunities": [], "warnings": [], "summary": {}})
        session.add_all([product, run])
        session.flush()
        product_id, run_id = product.id, run.id
    return module, factory, product_id, run_id, products[0], recall


def test_finalization_rollback(tmp_path):
    module, factory, product_id, run_id, product, recall = setup(tmp_path)
    from app.diwali.core import run_local
    state = run_local(replace(inputs(product, recall), run_id=UUID(run_id), product_ref=product_id))
    with pytest.raises(RuntimeError, match="commit boundary"), factory.begin() as session:
        module.stage_finalization(session, run_id, product_id, state)
        session.flush()
        raise RuntimeError("commit boundary")
    with factory() as session:
        assert session.scalar(select(Opportunity)) is None
        assert session.scalar(select(ClaimPacket)) is None
        assert session.scalar(select(module.CaseRow)) is None


def test_restart_cancels_tasks(tmp_path):
    module, factory, product_id, run_id, _product, _recall = setup(tmp_path)
    case_id = str(uuid4())
    with factory.begin() as session:
        session.add(module.CaseRow(id=case_id, run_id=run_id, product_id=product_id,
                                   phase="RESEARCHING", revision=1, payload={}))
        session.add(module.TaskRow(id=str(uuid4()), run_id=run_id, case_id=case_id,
                                   state="pending", payload={}))
    with factory.begin() as session:
        module.recover_interrupted(session)
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "failed"
        assert session.scalar(select(module.TaskRow)).state == "cancelled"


def test_stale_evidence(tmp_path):
    module, factory, product_id, run_id, product, recall = setup(tmp_path)
    from app.diwali.core import run_local
    state = run_local(replace(inputs(product, recall), run_id=UUID(run_id), product_ref=product_id))
    with factory.begin() as session:
        opp = module.stage_finalization(session, run_id, product_id, state)
        session.flush()
        packet = session.scalar(select(ClaimPacket))
        packet.payload = packet.payload | {"approved_at": "2026-11-15T00:00:00Z", "status": "approved_local"}
        packet_id = packet.id
        opp_id = opp.id
    with factory.begin() as session:
        entity = session.get(Product, product_id)
        entity.payload = entity.payload | {"product": product.model_copy(
            update={"model_number": "ZHX-PB23"}).model_dump(mode="json")}
    with factory.begin() as session:
        assert module.invalidate_stale(session, packet_id) is True
    with factory() as session:
        assert session.get(ClaimPacket, packet_id).payload["approved_at"] is None
        assert session.get(Opportunity, opp_id).payload["status"] == "needs_review"


def test_no_repeat_side_effect(tmp_path):
    module, factory, product_id, run_id, product, recall = setup(tmp_path)
    from app.diwali.core import run_local
    state = run_local(replace(inputs(product, recall), run_id=UUID(run_id), product_ref=product_id))
    with factory.begin() as session:
        module.stage_finalization(session, run_id, product_id, state)
    with factory.begin() as session:
        module.stage_finalization(session, run_id, product_id, state)
    with factory() as session:
        assert len(session.scalars(select(Opportunity)).all()) == 1
        assert len(session.scalars(select(ClaimPacket)).all()) == 1
        assert len(session.scalars(select(module.CaseRow)).all()) == 1


@pytest.mark.asyncio
async def test_completed_run_cannot_redispatch(tmp_path):
    from app.config import Settings
    from app.diwali.coordinator import execute
    from app.diwali.core import LocalTransport
    _module, factory, _product_id, run_id, _product, _recall = setup(tmp_path)
    class ObservedTransport(LocalTransport):
        def __init__(self):
            super().__init__()
            self.exchanges = 0
        def exchange(self, message, context):
            self.exchanges += 1
            return super().exchange(message, context)
    transport = ObservedTransport()
    with factory.begin() as session:
        session.get(AgentRun, run_id).status = "queued"
    await execute(factory, run_id, Settings(), transport)
    await execute(factory, run_id, Settings(), transport)
    assert transport.exchanges == 3
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "completed"


def test_competing_candidates_finalize_review_without_packet(tmp_path):
    module, factory, product_id, run_id, product, recall = setup(tmp_path)
    from app.diwali.core import run_local
    changed = recall.model_copy(update={"instructions": "Changed official terms"})
    context = replace(inputs(product, recall), run_id=UUID(run_id), product_ref=product_id,
                      records_json=(recall.model_dump_json(), changed.model_dump_json()))
    state = run_local(context)
    assert state.outcome == "needs_review"
    with factory.begin() as session:
        module.stage_finalization(session, run_id, product_id, state)
    with factory() as session:
        assert session.scalar(select(module.CaseRow)).payload["outcome"] == "needs_review"
        assert session.scalar(select(ClaimPacket)) is None


def test_unknown_schema_version_blocks_without_rebuilding_legacy(tmp_path):
    module, factory, product_id, _run_id, _product, _recall = setup(tmp_path)
    engine = factory.kw["bind"]
    module.setup_schema(engine)
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE diwali_schema_versions SET version=2")
    with pytest.raises(RuntimeError, match="schema version"):
        module.setup_schema(engine)
    with factory() as session:
        assert session.get(Product, product_id).model_number == "ZHX-PB22"


def test_snapshot_references_resolve_after_legacy_evidence_replacement(tmp_path):
    module, factory, product_id, run_id, product, recall = setup(tmp_path)
    from app.diwali.core import run_local
    state = run_local(replace(inputs(product, recall), run_id=UUID(run_id), product_ref=product_id))
    with factory.begin() as session:
        opportunity = module.stage_finalization(session, run_id, product_id, state)
        opportunity.payload = opportunity.payload | {"recall": recall.model_copy(
            update={"models": ["ZHX-PB23"]}).model_dump(mode="json")}
    with factory() as session:
        case = session.scalar(select(module.CaseRow))
        snapshot = case.payload["source_snapshots"][state.source_refs[0]]
        assert snapshot["record"]["models"] == ["ZHX-PB22"]
        assert snapshot["run_id"] == run_id
        assert len(snapshot["digest"]) == 64
