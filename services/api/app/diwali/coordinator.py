"""Only the coordinator owns V2 database writes. Actors receive frozen strings."""

import asyncio
import inspect
import json
from datetime import UTC, datetime
from time import monotonic
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.config import ROOT
from app.diwali.core import CaseInput, CaseState, Finalized, LocalTransport, Start, digest, reduce_case
from app.diwali.legacy_bridge import stage_finalization
from app.diwali.message_schema import validate_delivery
from app.diwali.persistence import CaseRow, InvocationRow, MessageRow, TaskRow, audit, surviving_results
from app.models import AgentRun, Product


class BudgetExceeded(ValueError):
    pass


def save_intent(session, run_id, product_id, state, command, *, mode="local"):
    message = command.message
    case = session.get(CaseRow, str(state.context.case_id))
    if case is None:
        case = CaseRow(id=str(state.context.case_id), run_id=run_id, product_id=product_id,
                       phase=state.phase, revision=state.revision, demo=True, payload={
                           "frozen_purchase": state.context.product.model_dump(mode="json"),
                           "source_snapshots": state.context.snapshot_registry,
                           "frozen_evidence": [r.model_dump(mode="json") for r in state.context.records]})
        session.add(case)
        session.flush()
    case.phase, case.revision = state.phase, state.revision
    session.add(TaskRow(id=str(message.task_id), run_id=run_id, case_id=case.id, state="pending", demo=True,
                        payload={"role": message.recipient, "deadline_at": message.deadline_at.isoformat(), "attempts": 0}))
    session.add(MessageRow(id=str(message.message_id), run_id=run_id, case_id=case.id,
        task_id=str(message.task_id), seq=None, digest=digest(message.model_dump(mode="json")),
        delivery="intent", demo=True, payload={"envelope": message.model_dump(mode="json"), "transport": mode}))


def consume(session, run_id, product_id, state, outgoing, incoming, *, mode="local", receipt=None):
    """Couple consumption, revision and next intent in one short transaction."""
    old = session.get(MessageRow, str(incoming.message_id))
    fingerprint = digest(incoming.model_dump(mode="json"))
    if old:
        if old.digest != fingerprint:
            raise ValueError("Conflicting message ID reuse")
        return state, ()
    task = session.get(TaskRow, str(incoming.task_id))
    if task is None:
        raise ValueError("Unknown task result")
    if task.state != "pending":
        return state, ()
    state, commands = reduce_case(state, incoming, observed_at=datetime.now(UTC))
    seq = (session.scalar(select(func.max(MessageRow.seq)).where(MessageRow.run_id == run_id)) or 0) + 1
    intent = session.get(MessageRow, str(outgoing.message_id))
    intent.seq, intent.delivery = seq, "consumed"
    intent.payload = intent.payload | {"received": True, "consumed": True}
    session.add(MessageRow(id=str(incoming.message_id), run_id=run_id, case_id=str(state.context.case_id),
        task_id=str(incoming.task_id), seq=seq + 1, digest=fingerprint, delivery="consumed", demo=True,
        payload={"envelope": incoming.model_dump(mode="json"), "transport": mode, "received": True,
                 "consumed": True}))
    if mode == "band":
        if not receipt or not receipt.get("request_id") or not receipt.get("result_id"):
            raise ValueError("BAND result lacks confirmed transport receipt")
        session.add(InvocationRow(task_id=task.id, provider="band", mode="live", demo=True,
            payload=dict(receipt) | {"received": True, "consumed": True}))
        if receipt.get("reviewer"):
            review = dict(receipt["reviewer"])
            session.add(InvocationRow(task_id=task.id, provider="lyzr", mode=review["mode"], demo=True,
                payload=review | {"received": True, "consumed": True}))
            run = session.get(AgentRun, run_id)
            run.payload = run.payload | {"reviewer_mode": "lyzr" if review["mode"] == "live" else "fixture",
                "provider_modes": run.payload.get("provider_modes", {}) | {
                    "lyzr": review.get("status", "validated")}}
    task.state = "consumed"
    case = session.get(CaseRow, str(state.context.case_id))
    case.phase = "FINALIZING" if any(c.finalize for c in commands) else state.phase
    case.revision = state.revision
    for command in commands:
        if command.message:
            save_intent(session, run_id, product_id, state, command, mode=mode)
        if command.finalize:
            stage_finalization(session, run_id, product_id, state)
    return state, commands


async def drive(factory, run_id, settings, transport, *, started):
    mode = transport.mode
    with factory.begin() as session:
        run = session.get(AgentRun, run_id)
        if run is None or run.status != "queued":
            return
        run.status = "running"
        run.payload = run.payload | {"actual_transport": mode, "source_mode": "recorded", "reviewer_mode": "rules"}
        product_ids = [session.scalar(select(Product.id).where(Product.purchase_id == p))
                       for p in run.payload["purchase_ids"]]
    try:
        for product_id in product_ids:
            with factory() as session:
                product = session.get(Product, product_id).payload["product"]
            context = CaseInput(run_id=UUID(run_id), case_id=uuid4(), product_ref=product_id,
                product_json=json.dumps(product),
                records_json=((ROOT / "demo/recall_fixture.json").read_text(),),
                task_ids=tuple(uuid4() for _ in range(5)), started_at=datetime.now(UTC),
                max_followups=settings.diwali_max_followups_per_case,
                settlement_json=(ROOT / "demo/settlement_fixture.json").read_text())
            state, commands = reduce_case(CaseState(context), Start())
            with factory.begin() as session:
                save_intent(session, run_id, product_id, state, commands[0], mode=mode)
            messages = 0
            while commands:
                outgoing = next((c.message for c in commands if c.message), None)
                if outgoing is None:
                    break
                if monotonic() - started >= settings.diwali_max_run_seconds - 5:
                    raise TimeoutError("Run deadline")
                if messages + 2 > settings.diwali_max_messages_per_case:
                    raise BudgetExceeded("Application message budget")
                task_started = monotonic()
                task_budget = min(settings.diwali_remote_task_seconds,
                                  settings.diwali_max_run_seconds - 5 - (task_started - started))
                with factory.begin() as session:
                    task = session.get(TaskRow, str(outgoing.task_id))
                    if task.payload["attempts"] != 0:
                        raise ValueError("Task already attempted; no automatic retry")
                    task.payload = task.payload | {"attempts": 1}
                    session.get(MessageRow, str(outgoing.message_id)).delivery = "dispatching"
                if monotonic() - task_started >= task_budget:
                    raise TimeoutError("Task deadline exceeded before dispatch")
                async with asyncio.timeout(task_budget):
                    incoming = transport.exchange(outgoing, context)
                    if inspect.isawaitable(incoming):
                        incoming = await incoming
                if monotonic() - task_started >= task_budget:
                    raise TimeoutError("Task deadline exceeded")
                if incoming.task_id != outgoing.task_id or incoming.causation_id != outgoing.message_id:
                    raise ValueError("Response does not belong to dispatched task")
                validate_delivery(incoming, transport.identities[outgoing.recipient],
                                  transport.identities["manager"], transport.identities)
                with factory.begin() as session:
                    state, commands = consume(session, run_id, product_id, state, outgoing, incoming,
                        mode=mode, receipt=getattr(transport, "last_receipt", None))
                messages += 2
            if state.phase == "FINALIZING":
                state, _ = reduce_case(state, Finalized())
        with factory.begin() as session:
            run = session.get(AgentRun, run_id)
            cases = session.scalars(select(CaseRow).where(CaseRow.run_id == run_id)).all()
            failures = [c.payload.get("failure") for c in cases if c.payload.get("failure")]
            valid = [c.payload.get("outcome") for c in cases if c.payload.get("outcome")]
            run.status = "partial" if failures and valid else "failed" if failures else "completed"
            run.payload = run.payload | {"warnings": failures, "summary": {
                "products_scanned": len(cases), "verified_matches": valid.count("verified_match"),
                "rejected": valid.count("rejected"), "needs_review": valid.count("needs_review"),
                "simulated_settlements": valid.count("simulated_settlement"),
                "prepared_packets": valid.count("verified_match"),
            }}
            audit(session, run, "RunCompleted" if run.status == "completed" else "RunPartial")
    except Exception as exc:  # noqa: BLE001 -- sanitize task failure
        record_failure(factory, run_id, exc)


def record_failure(factory, run_id, exc):
    with factory.begin() as session:
        run = session.get(AgentRun, run_id)
        cases = session.scalars(select(CaseRow).where(CaseRow.run_id == run_id)).all()
        run.status = "partial" if surviving_results(session, run_id) else "failed"
        reason = ("DEADLINE" if isinstance(exc, TimeoutError) else "BUDGET_EXHAUSTED"
                  if isinstance(exc, BudgetExceeded) else "INVALID_RESULT")
        run.payload = run.payload | {"warnings": [f"{reason}: explicit new run required"]}
        for task in session.scalars(select(TaskRow).where(TaskRow.run_id == run_id, TaskRow.state == "pending")):
            task.state = "cancelled"
        for case in cases:
            if not case.payload.get("outcome"):
                case.phase = "DONE"
                case.payload = case.payload | {"failure": reason}


async def execute(factory, run_id, settings, transport=None):
    started = monotonic()
    with factory() as session:
        run = session.get(AgentRun, run_id)
        if run is None or run.status != "queued":
            return
        requested = run.payload.get("collaboration_mode", "local")
    if transport is not None or requested != "band":
        return await drive(factory, run_id, settings, transport or LocalTransport(), started=started)
    from app.diwali.band_bridge import BandTransport
    from app.diwali.band_settings import credentials, validate_synthetic
    try:
        with factory() as session:
            validate_synthetic(session, session.get(AgentRun, run_id).payload["purchase_ids"])
        options = {}
        if settings.lyzr_enabled:
            from app.diwali.lyzr_review import LyzrReviewer
            skill = None
            if settings.finch_enabled:
                from app.diwali.finch_skill import load_configured_skill
                skill = load_configured_skill(settings)
            options["reviewer"] = LyzrReviewer(settings.lyzr_api_key, settings.lyzr_review_agent_id,
                max_calls=settings.diwali_max_lyzr_calls_per_run, skill=skill)
        async with asyncio.timeout(settings.diwali_max_run_seconds - 5):
            async with BandTransport(credentials(settings), **options) as remote:
                await drive(factory, run_id, settings, remote, started=started)
    except Exception as exc:  # noqa: BLE001 -- no credentials/provider details in public output
        record_failure(factory, run_id, exc)
