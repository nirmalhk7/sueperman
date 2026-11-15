"""Faults keep valid evidence, close work and never invent completion."""

from uuid import UUID

import pytest
from sqlalchemy import select
from test_persistence import setup

from app.config import Settings
from app.diwali.coordinator import execute
from app.diwali.core import LocalTransport
from app.models import AgentRun, ClaimPacket


def queued(factory, run_id):
    with factory.begin() as session:
        session.get(AgentRun, run_id).status = "queued"


@pytest.mark.asyncio
async def test_malformed_result_closes_case_without_packet(tmp_path):
    module, factory, _p, run_id, _product, _recall = setup(tmp_path)
    class Malformed(LocalTransport):
        def exchange(self, message, context):
            return {"status": "verified_match", "secret": "must-not-be-logged"}
    queued(factory, run_id)
    await execute(factory, run_id, Settings(), Malformed())
    with factory() as session:
        run = session.get(AgentRun, run_id)
        assert run.status == "failed"
        case = session.scalar(select(module.CaseRow))
        assert case.phase == "DONE"
        assert case.payload["failure"] == "INVALID_RESULT"
        assert case.payload["frozen_evidence"]
        assert session.scalar(select(ClaimPacket)) is None
        assert all(t.state == "cancelled" for t in session.scalars(select(module.TaskRow)))
        assert "must-not-be-logged" not in str(run.payload)


@pytest.mark.asyncio
async def test_task_deadline_rejects_late_result(tmp_path, monkeypatch):
    module, factory, _p, run_id, _product, _recall = setup(tmp_path)
    elapsed = [0.0]
    monkeypatch.setattr("app.diwali.coordinator.monotonic", lambda: elapsed[0])
    class Late(LocalTransport):
        def exchange(self, message, context):
            elapsed[0] += 11
            return super().exchange(message, context)
    queued(factory, run_id)
    await execute(factory, run_id, Settings(), Late())
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "failed"
        assert session.scalar(select(module.CaseRow)).payload["failure"] == "DEADLINE"
        assert session.scalar(select(ClaimPacket)) is None


@pytest.mark.asyncio
async def test_finalization_error_preserves_accepted_reports(tmp_path, monkeypatch):
    module, factory, _p, run_id, _product, _recall = setup(tmp_path)
    def fail(*args):
        raise RuntimeError("private provider detail")
    monkeypatch.setattr("app.diwali.coordinator.stage_finalization", fail)
    queued(factory, run_id)
    await execute(factory, run_id, Settings())
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "partial"
        assert session.scalar(select(ClaimPacket)) is None
        # Builder result and domain commit roll back together; earlier accepted reports survive.
        rows = session.scalars(select(module.MessageRow).where(module.MessageRow.delivery == "consumed")).all()
        assert [r.payload["envelope"]["type"] for r in sorted(rows, key=lambda r: r.seq)] == [
            "ResearchRequested", "ResearchReport", "ReviewRequested", "ReviewReport"]


@pytest.mark.asyncio
async def test_intent_saved_and_session_closed_before_dispatch(tmp_path):
    module, factory, _p, run_id, _product, _recall = setup(tmp_path)
    engine = factory.kw["bind"]
    class Observed(LocalTransport):
        def exchange(self, message, context):
            assert engine.pool.checkedout() == 0
            with factory() as session:
                task = session.get(module.TaskRow, str(message.task_id))
                intent = session.get(module.MessageRow, str(message.message_id))
                assert task.state == "pending"
                assert task.payload["attempts"] == 1
                assert intent.delivery == "dispatching"
                assert intent.seq is None
            return super().exchange(message, context)
    queued(factory, run_id)
    await execute(factory, run_id, Settings(), Observed())
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "completed"


@pytest.mark.asyncio
async def test_odd_message_budget_never_overshoots(tmp_path):
    module, factory, _p, run_id, _product, _recall = setup(tmp_path)
    queued(factory, run_id)
    await execute(factory, run_id, Settings(diwali_max_messages_per_case=3))
    with factory() as session:
        accepted = session.scalars(select(module.MessageRow).where(module.MessageRow.delivery == "consumed")).all()
        assert len(accepted) == 2
        assert session.get(AgentRun, run_id).status == "partial"
        assert session.scalar(select(module.CaseRow)).payload["failure"] == "BUDGET_EXHAUSTED"


@pytest.mark.asyncio
async def test_wrong_task_result_cannot_complete_run(tmp_path):
    module, factory, _p, run_id, _product, _recall = setup(tmp_path)
    class WrongTask(LocalTransport):
        def exchange(self, message, context):
            return super().exchange(message, context).model_copy(update={"task_id": UUID(int=999)})
    queued(factory, run_id)
    await execute(factory, run_id, Settings(), WrongTask())
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "failed"
        assert session.scalar(select(module.CaseRow)).payload["failure"] == "INVALID_RESULT"
        assert session.scalar(select(ClaimPacket)) is None
