from datetime import date

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.collaboration.contracts import Answer, Approval, RevisionRequest, Start
from app.collaboration.controller import execute, sanitized
from app.collaboration.ledger import ACTIVE, current, digest
from app.collaboration.revisions import revoke_if_changed
from app.models import (
    Collaboration,
    CollaborationRevision,
    CollaborationTask,
    CollaborationUsage,
    Product,
    now,
)
from app.schemas import ProductInput


def case_view(s, case):
    revoke_if_changed(s, case)
    revision = current(s, case)
    data = revision.payload if revision else {}
    return {
        "id": case.id,
        "product_id": case.product_id,
        "status": case.status,
        "revision": case.current_revision,
        "mode": case.payload["mode"],
        "live_sponsor_proof": False,
        "board": data.get("board", {}),
        "question": data.get("question"),
        "packet": data.get("packet"),
        "approval": data.get("approval"),
        "warnings": case.payload.get("warnings", []),
        "blocked_providers": case.payload.get("blocked_providers", []),
        "conditions": data.get("conditions", []),
        "elapsed_ms": case.payload.get("elapsed_ms"),
        "model_calls": case.payload.get("model_calls", 0),
        "task_requests": case.payload.get("task_requests", 0),
        "skill": {
            "mode": "local_replay" if case.payload["mode"] == "replay" else "pinned_package",
            "hash": data.get("skill_hash"),
            "identity": data.get("skill_identity"),
            "version": data.get("skill_version"),
            "finch_delivered": False,
        },
        "history": [
            {
                "revision": r.revision,
                "created_at": r.created_at,
                "board": r.payload.get("board"),
                "evidence": r.payload.get("evidence", []),
            }
            for r in s.scalars(
                select(CollaborationRevision)
                .where(CollaborationRevision.case_id == case.id)
                .order_by(CollaborationRevision.created_at)
            )
        ],
    }


def checked_revision(s, case, revision):
    if case.current_revision != revision:
        raise HTTPException(409, "Stale case revision; refresh before continuing")
    reason = revoke_if_changed(s, case)
    if reason:
        raise HTTPException(409, reason)
    row = current(s, case)
    if not row:
        raise HTTPException(409, "Case revision unavailable")
    return row


def reserve_run(s, settings):
    # Caller holds BEGIN IMMEDIATE; demo reset deliberately preserves this counter.
    if s.scalar(select(Collaboration).where(Collaboration.status.in_(ACTIVE))):
        raise HTTPException(409, "A team investigation is already active")
    day = now()[:10]
    usage = s.get(CollaborationUsage, day)
    if (usage.calls if usage else 0) >= settings.collaboration_daily_limit:
        raise HTTPException(429, "Daily synthetic team run limit reached")
    if usage is None:
        s.add(CollaborationUsage(day=day, calls=1))
    else:
        usage.calls += 1


def register(app, factory, settings, get):
    @app.post("/api/collaborations")
    def start(body: Start, background: BackgroundTasks):
        with factory() as s:
            s.execute(text("BEGIN IMMEDIATE"))
            old = s.scalar(select(Collaboration).where(Collaboration.idempotency_key == body.idempotency_key))
            if old:
                if old.product_id != body.product_ids[0] or old.payload["mode"] != body.mode:
                    raise HTTPException(409, "Idempotency key already used for different input")
                return case_view(s, old)
            product = get(s, Product, body.product_ids[0])
            if not product.demo:
                raise HTTPException(422, "Public V2 supports synthetic demo purchases only")
            if not settings.demo_mode:
                raise HTTPException(422, "Synthetic demo disabled")
            reserve_run(s, settings)
            case = Collaboration(
                product_id=product.id,
                idempotency_key=body.idempotency_key,
                demo=True,
                payload={"mode": body.mode, "facts": sanitized(product.payload["product"]), "warnings": []},
            )
            s.add(case)
            try:
                s.commit()
            except IntegrityError:
                s.rollback()
                raise HTTPException(409, "Duplicate investigation") from None
            background.add_task(execute, factory, case.id, settings)
            return case_view(s, case)

    @app.get("/api/collaborations/{identifier}")
    def detail(identifier: str):
        with factory() as s:
            return case_view(s, get(s, Collaboration, identifier))

    @app.get("/api/collaborations/{identifier}/events")
    def events(identifier: str):
        with factory() as s:
            get(s, Collaboration, identifier)
            events = []
            for row in s.scalars(
                select(CollaborationTask)
                .where(CollaborationTask.case_id == identifier)
                .order_by(CollaborationTask.seq)
            ):
                task = row.payload["task"]
                shared = {
                    k: task[k]
                    for k in ["sender", "recipient", "mode", "task_kind", "revision", "source_refs"]
                }
                events.append(
                    shared
                    | {
                        "seq": row.seq * 2 - 1,
                        "kind": "request",
                        "status": row.status,
                        "provider": "local_replay"
                        if task["mode"] == "replay"
                        else {"scout": "agent37", "skeptic": "adal", "builder": "lyzr"}[task["recipient"]],
                        "timestamp": row.created_at,
                    }
                )
                result = row.payload.get("result")
                if result:
                    events.append(
                        shared
                        | {
                            "seq": row.seq * 2,
                            "kind": "result",
                            "sender": task["recipient"],
                            "recipient": task["sender"],
                            "status": result["status"],
                            "provider": result["provider"],
                            "findings": result["findings"],
                            "timestamp": row.updated_at,
                        }
                    )
            return events

    @app.post("/api/collaborations/{identifier}/answers")
    def answer(identifier: str, body: Answer, background: BackgroundTasks):
        with factory() as s:
            s.execute(text("BEGIN IMMEDIATE"))
            case = get(s, Collaboration, identifier)
            row = checked_revision(s, case, body.revision)
            question = row.payload.get("question")
            if case.status != "needs_information" or not question or body.field != question["field"]:
                raise HTTPException(409, "Only the current requested field can be answered")
            facts = row.payload["facts"] | {body.field: body.value}
            try:
                if body.field == "date_purchased":
                    date.fromisoformat(body.value)
                ProductInput(**facts)
            except (ValueError, ValidationError):
                raise HTTPException(422, "Invalid requested field") from None
            if facts == row.payload["facts"]:
                raise HTTPException(409, "Answer does not change the unresolved fact")
            reserve_run(s, settings)
            row.payload = row.payload | {"approval": None}
            case.payload = case.payload | {"facts": facts}
            case.status = "queued"
            s.commit()
            background.add_task(execute, factory, case.id, settings)
            return case_view(s, case)

    @app.post("/api/collaborations/{identifier}/approve-local")
    def approve(identifier: str, body: Approval):
        with factory() as s:
            s.execute(text("BEGIN IMMEDIATE"))
            case = get(s, Collaboration, identifier)
            row = checked_revision(s, case, body.revision)
            if case.status != "ready_for_review" or not row.payload["packet"]:
                raise HTTPException(409, "Deterministic checks have not passed")
            row.payload = row.payload | {
                "approval": {
                    "revision": body.revision,
                    "packet_hash": digest(row.payload["packet"]),
                    "approved_at": now(),
                }
            }
            s.commit()
            return case_view(s, case)

    @app.post("/api/collaborations/{identifier}/export")
    def export(identifier: str, body: RevisionRequest):
        with factory() as s:
            case = get(s, Collaboration, identifier)
            row = checked_revision(s, case, body.revision)
            approval = row.payload.get("approval")
            if (
                case.status != "ready_for_review"
                or not approval
                or approval["revision"] != body.revision
                or approval["packet_hash"] != digest(row.payload["packet"])
            ):
                raise HTTPException(409, "Review and approve the current local draft before export")
            markdown = row.payload["packet"]["markdown"] + "\n\nCase revision: " + body.revision
            return Response(
                markdown,
                media_type="text/markdown",
                headers={"Content-Disposition": 'attachment; filename="sueperman-team-draft.md"'},
            )
