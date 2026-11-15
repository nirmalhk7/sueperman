"""Append-only case history. Caller serializes case mutations in one transaction."""

import hashlib
import json
from typing import cast
from uuid import uuid4

from sqlalchemy import Table, func, select

from app.collaboration.contracts import CaseResult, CaseRevision, CaseTask, DraftApproval, validate_result
from app.models import (
    CaseDraft,
    CaseRecord,
    CaseRevisionRecord,
    CaseSnapshot,
    CollaborationEvent,
    CollaborationRun,
    CollaborationTask,
    now,
)

TABLES = [
    CaseRecord,
    CaseRevisionRecord,
    CollaborationRun,
    CollaborationTask,
    CollaborationEvent,
    CaseSnapshot,
    CaseDraft,
]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def migrate(engine):
    """V2 additive migration 001: create missing tables only; never alter V1 data.

    SQLAlchemy table creation checks existence, including indexes and unique
    constraints on first creation. No DROP, reset or rewriting JSON columns.
    """
    with engine.begin() as connection:
        for model in TABLES:
            cast(Table, model.__table__).create(connection, checkfirst=True)


def create_case(s, product_id):
    case = CaseRecord(
        product_id=product_id, demo=True, current_revision=0, payload={"answers": {}, "current_run_id": None}
    )
    s.add(case)
    s.flush()
    return case


def revise(s, case, binding):
    typed = CaseRevision(**binding)
    data = typed.model_dump(mode="json")
    digest = fingerprint(data)
    previous = current_revision(s, case)
    if previous and previous.fingerprint == digest:
        return previous
    case.current_revision += 1
    revision = CaseRevisionRecord(
        case_id=case.id, revision=case.current_revision, fingerprint=digest, demo=case.demo, payload=data
    )
    s.add(revision)
    # Approval history remains inspectable; revocation is explicit and immediate.
    for draft in s.scalars(select(CaseDraft).where(CaseDraft.case_id == case.id)):
        if draft.payload.get("approval"):
            draft.payload = draft.payload | {"revoked_at": now(), "status": "needs_review"}
    s.flush()
    return revision


def current_revision(s, case):
    return s.scalar(
        select(CaseRevisionRecord).where(
            CaseRevisionRecord.case_id == case.id, CaseRevisionRecord.revision == case.current_revision
        )
    )


def create_run(s, case, key, mode):
    old = s.scalar(select(CollaborationRun).where(CollaborationRun.idempotency_key == key))
    if old:
        if old.case_id != case.id or old.payload["mode"] != mode:
            raise ValueError("Idempotency key already used for different input")
        return old
    run = CollaborationRun(
        case_id=case.id,
        revision=case.current_revision,
        idempotency_key=key,
        demo=case.demo,
        payload={"mode": mode, "warnings": [], "board": {}, "model_calls": 0, "task_requests": 0},
    )
    s.add(run)
    s.flush()
    case.payload = case.payload | {"current_run_id": run.id}
    return run


def event(s, run, data):
    seq = (
        s.scalar(select(func.max(CollaborationEvent.seq)).where(CollaborationEvent.run_id == run.id)) or 0
    ) + 1
    s.add(
        CollaborationEvent(
            run_id=run.id,
            seq=seq,
            demo=run.demo,
            payload=data | {"timestamp": now(), "mode": run.payload["mode"]},
        )
    )
    s.flush()


def record_intent(s, run, task: CaseTask):
    case = s.get(CaseRecord, run.case_id)
    if task.case_id != case.id or task.revision != case.current_revision or run.revision != task.revision:
        raise ValueError("Stale case revision")
    old = s.scalar(
        select(CollaborationTask).where(
            CollaborationTask.run_id == run.id, CollaborationTask.deduplication_key == task.deduplication_key
        )
    )
    if old:
        if old.payload["task"] != task.model_dump(mode="json"):
            raise ValueError("Conflicting task delivery")
        return old
    count = s.scalar(
        select(func.count()).select_from(CollaborationTask).where(CollaborationTask.run_id == run.id)
    )
    if count >= 6:
        raise ValueError("Task request budget exhausted")
    row = CollaborationTask(
        id=task.task_id,
        run_id=run.id,
        deduplication_key=task.deduplication_key,
        demo=run.demo,
        payload={"task": task.model_dump(mode="json"), "result": None},
    )
    s.add(row)
    event(
        s,
        run,
        {
            "kind": "request",
            "sender": task.sender,
            "recipient": task.recipient,
            "task_kind": task.kind,
            "task_id": task.task_id,
            "source_refs": task.source_refs,
        },
    )
    return row


def record_result(s, run, task: CaseTask, result: CaseResult, available):
    case = s.get(CaseRecord, run.case_id)
    if case.current_revision != task.revision or run.revision != task.revision:
        raise ValueError("Stale case revision")
    validate_result(task, result, available)
    row = s.get(CollaborationTask, task.task_id)
    if row is None or row.run_id != run.id or row.payload["task"] != task.model_dump(mode="json"):
        raise ValueError("Result without persisted intent")
    if row.payload["result"] is not None:
        if row.payload["result"] != result.model_dump(mode="json"):
            raise ValueError("Conflicting result delivery")
        return False
    # Routing references stay private; events never include raw provider text.
    if run.status not in {"queued", "investigating", "challenging", "building"}:
        raise ValueError("Result for closed run")
    row.payload = row.payload | {"result": result.model_dump(mode="json")}
    event(
        s,
        run,
        {
            "kind": "result",
            "sender": task.recipient,
            "recipient": "controller",
            "task_kind": task.kind,
            "task_id": task.task_id,
            "provider": result.provider,
            "status": result.status,
            "source_refs": result.source_refs,
            "findings": [f.model_dump() for f in result.findings],
        },
    )
    return True


def prepare_draft(s, case, markdown):
    draft = s.scalar(
        select(CaseDraft).where(CaseDraft.case_id == case.id, CaseDraft.revision == case.current_revision)
    )
    if draft is None:
        draft = CaseDraft(
            id=str(uuid4()),
            case_id=case.id,
            revision=case.current_revision,
            demo=case.demo,
            payload={
                "markdown": markdown,
                "status": "ready_for_review",
                "approval": None,
                "revoked_at": None,
            },
        )
        s.add(draft)
        s.flush()
    elif draft.payload["markdown"] != markdown:
        raise ValueError("Changed draft requires new revision")
    return draft


def approve_draft(s, case, draft):
    if draft.revision != case.current_revision or draft.payload.get("revoked_at"):
        raise ValueError("Current revision requires new review")
    revision = current_revision(s, case)
    approval = DraftApproval(
        packet_hash=fingerprint(draft.payload["markdown"]), revision_fingerprint=revision.fingerprint
    )
    draft.payload = draft.payload | {
        "approval": approval.model_dump(),
        "approved_at": now(),
        "status": "approved_local",
    }


def export_draft(s, case, draft):
    revision = current_revision(s, case)
    expected = {
        "packet_hash": fingerprint(draft.payload["markdown"]),
        "revision_fingerprint": revision.fingerprint,
    }
    if (
        draft.revision != case.current_revision
        or draft.payload.get("revoked_at")
        or draft.payload.get("approval") != expected
    ):
        raise ValueError("Current draft requires local review")
    draft.payload = draft.payload | {"status": "exported"}
    return draft.payload["markdown"]


def recover_interrupted(s):
    for run in s.scalars(
        select(CollaborationRun).where(
            CollaborationRun.status.in_(["queued", "investigating", "challenging", "building"])
        )
    ):
        run.status = "partial"
        run.payload = run.payload | {"warnings": ["Controller restarted; unconfirmed work is partial."]}
        event(
            s,
            run,
            {
                "kind": "interrupted",
                "sender": "controller",
                "recipient": "controller",
                "status": "partial",
                "source_refs": [],
            },
        )
