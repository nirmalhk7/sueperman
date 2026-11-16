"""Remote time and transport boundaries use real reducer/database behavior."""

from datetime import timedelta

from test_local_core import fixture_data, inputs

from app.diwali.core import CaseState, LocalTransport, Start, reduce_case


def test_each_stage_gets_its_own_ten_second_deadline():
    products, recall = fixture_data()
    context = inputs(products[0], recall)
    state, commands = reduce_case(CaseState(context), Start())
    request = commands[0].message
    transport = LocalTransport()
    for elapsed, wanted_type in [(6, "ReviewRequested"), (12, "BuildRequested")]:
        response = transport.exchange(request, context)
        observed = context.started_at + timedelta(seconds=elapsed)
        try:
            state, commands = reduce_case(state, response, observed_at=observed)
        except TypeError:
            # The old reducer always dated every task from the case start.
            state, commands = reduce_case(state, response)
        request = commands[0].message
        assert request.type == wanted_type
        assert request.sent_at == observed
        assert request.deadline_at == observed + timedelta(seconds=10)


async def test_async_transport_consumes_outcome_and_commits_no_session_across_await(tmp_path):
    import asyncio

    from sqlalchemy import select
    from test_persistence import setup

    from app.config import Settings
    from app.diwali.coordinator import execute
    from app.diwali.persistence import InvocationRow, MessageRow
    from app.models import AgentRun, ClaimPacket

    _module, factory, _product_id, run_id, _product, _recall = setup(tmp_path)
    with factory.begin() as session:
        run = session.get(AgentRun, run_id)
        run.status = "queued"
        run.payload = run.payload | {"collaboration_mode": "band"}

    class OfflineBandBoundary(LocalTransport):
        mode = "band"
        last_receipt = None

        async def exchange(self, message, context):
            with factory.begin() as independent:
                independent.connection().exec_driver_sql("BEGIN IMMEDIATE")
            await asyncio.sleep(0)
            result = super().exchange(message, context)
            self.last_receipt = {"request_id": f"platform-request-{message.type}",
                "result_id": f"platform-result-{message.type}", "authenticated_sender": self.identities[message.recipient]}
            return result

    await execute(factory, run_id, Settings(_env_file=None), transport=OfflineBandBoundary())
    with factory() as session:
        run = session.get(AgentRun, run_id)
        assert run.status == "completed", run.payload
        assert run.payload["actual_transport"] == "band"
        packet = session.scalar(select(ClaimPacket))
        assert packet.payload["approved_at"] is None
        assert "ZHX-PB22" in packet.payload["markdown"]
        messages = session.scalars(select(MessageRow).where(MessageRow.delivery == "consumed")).all()
        assert len(messages) == 6
        assert all(m.payload["transport"] == "band" for m in messages)
        invocations = session.scalars(select(InvocationRow)).all()
        assert len(invocations) == 3
        assert all(i.payload["received"] and i.payload["consumed"] for i in invocations)


async def test_async_timeout_is_one_attempt_without_local_fallback(tmp_path):
    import asyncio

    from sqlalchemy import select
    from test_persistence import setup

    from app.config import Settings
    from app.diwali.coordinator import execute
    from app.models import AgentRun, ClaimPacket

    _module, factory, _product_id, run_id, _product, _recall = setup(tmp_path)
    with factory.begin() as session:
        session.get(AgentRun, run_id).status = "queued"

    class OfflineTimeout(LocalTransport):
        mode = "band"
        attempts = 0

        async def exchange(self, message, context):
            self.attempts += 1
            await asyncio.sleep(10)

    transport = OfflineTimeout()
    await execute(factory, run_id, Settings(_env_file=None, diwali_remote_task_seconds=0.01), transport=transport)
    assert transport.attempts == 1
    with factory() as session:
        run = session.get(AgentRun, run_id)
        assert run.status == "failed"
        assert run.payload["warnings"] == ["DEADLINE: explicit new run required"]
        assert session.scalar(select(ClaimPacket)) is None


async def test_failed_enabled_reviewer_persists_attempt_and_never_claims_rules_fallback(tmp_path):
    from sqlalchemy import select
    from test_persistence import setup

    from app.config import Settings
    from app.diwali.coordinator import execute
    from app.diwali.core import failure_reply
    from app.diwali.persistence import InvocationRow
    from app.models import AgentRun, ClaimPacket

    _module, factory, _product_id, run_id, _product, _recall = setup(tmp_path)
    with factory.begin() as session:
        session.get(AgentRun, run_id).status = "queued"

    class FailedReviewBoundary(LocalTransport):
        mode = "band"
        last_receipt = None

        async def exchange(self, message, context):
            self.last_receipt = {"request_id": "offline-request", "result_id": "offline-result"}
            if message.type == "ReviewRequested":
                self.last_receipt["reviewer"] = {"mode": "live", "status": "failed_or_unknown", "attempts": 1}
                return failure_reply(message, "INVALID_RESULT")
            assert message.type != "BuildRequested"
            return super().exchange(message, context)

    await execute(factory, run_id, Settings(_env_file=None), transport=FailedReviewBoundary())
    with factory() as session:
        run = session.get(AgentRun, run_id)
        assert run.status == "failed"
        assert run.payload["reviewer_mode"] == "lyzr"
        assert run.payload["provider_modes"]["lyzr"] == "failed_or_unknown"
        attempts = session.scalars(select(InvocationRow).where(InvocationRow.provider == "lyzr")).all()
        assert len(attempts) == 1
        assert attempts[0].payload["status"] == "failed_or_unknown"
        assert session.scalar(select(ClaimPacket)) is None
