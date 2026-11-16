"""Append-only revision/evidence history and idempotent addressed task delivery."""

import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from app.collaboration.contracts import CaseResult, CaseTask
from app.models import Collaboration, CollaborationRevision, CollaborationTask

RULE_VERSION = "cpsc-26-792-counterexample-v1"
_POLICY_BYTES = Path(__file__).with_name("local_policy.json").read_bytes()
LOCAL_POLICY = json.loads(_POLICY_BYTES)
LOCAL_SKILL_HASH = hashlib.sha256(_POLICY_BYTES).hexdigest()
ACTIVE = ["queued", "investigating", "challenging", "building"]


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def revision_for(product, evidence, skill_hash=LOCAL_SKILL_HASH, rule_version=RULE_VERSION):
    return digest(
        {"product": product, "evidence": evidence, "rule_version": rule_version, "skill_hash": skill_hash}
    )


def current(s, case):
    return s.scalar(
        select(CollaborationRevision).where(
            CollaborationRevision.case_id == case.id, CollaborationRevision.revision == case.current_revision
        )
    )


def persist_intent(s, case, task: CaseTask):
    if task.case_id != case.id or task.revision != case.current_revision:
        raise ValueError("Stale or wrong-case task")
    route = {
        "scout": ("controller", "source_investigation"),
        "skeptic": ("scout", "counterexample_review"),
        "builder": ("skeptic", "case_board_construction"),
    }
    if (task.sender, task.task_kind) != route[task.recipient]:
        raise ValueError("Unregistered participant or invalid delegation")
    old = s.scalar(
        select(CollaborationTask).where(CollaborationTask.deduplication_key == task.deduplication_key)
    )
    if old:
        if old.payload["task"] != task.model_dump(mode="json"):
            raise ValueError("Deduplication key conflicts with task")
        return old
    prior = s.scalars(select(CollaborationTask).where(CollaborationTask.case_id == case.id)).all()
    if sum(t.revision == task.revision for t in prior) >= LOCAL_POLICY["max_task_requests"]:
        raise ValueError("Task budget exhausted")
    if task.parent_task_id:
        parent = s.get(CollaborationTask, task.parent_task_id)
        if (
            not parent
            or parent.case_id != case.id
            or (
                parent.revision != task.revision
                and not (
                    task.recipient == "skeptic"
                    and current(s, case)
                    and current(s, case).payload.get("origin_scout_task") == parent.id
                    and parent.payload["task"]["recipient"] == "scout"
                )
            )
            or parent.status != "completed"
        ):
            raise ValueError("Delegation requires a completed same-revision parent")
    row = CollaborationTask(
        id=task.task_id,
        case_id=case.id,
        revision=task.revision,
        deduplication_key=task.deduplication_key,
        seq=len(prior) + 1,
        demo=case.demo,
        payload={"task": task.model_dump(mode="json")},
    )
    s.add(row)
    s.commit()  # Dispatch cannot happen before intent is durable.
    return row


def persist_result(s, case, row, result: CaseResult):
    if (result.case_id, result.revision, result.task_id) != (case.id, case.current_revision, row.id):
        raise ValueError("Stale or wrong-case result")
    task = CaseTask(**row.payload["task"])
    expected_provider = (
        "local_replay"
        if task.mode == "replay"
        else {"scout": "agent37", "skeptic": "adal", "builder": "lyzr"}[task.recipient]
    )
    if result.provider != expected_provider:
        raise ValueError("Unexpected provider attribution")
    if result.role != task.recipient or result.mode != task.mode:
        raise ValueError("Unexpected role or mode")
    if not set(result.source_refs).issubset(task.source_refs):
        raise ValueError("Fabricated citation")
    if any(f.source_ref and f.source_ref not in result.source_refs for f in result.findings):
        raise ValueError("Finding cites unavailable evidence")
    data = result.model_dump(mode="json")
    if row.payload.get("result"):
        if row.payload["result"] != data:
            raise ValueError("Conflicting duplicate result")
        return
    row.payload = row.payload | {"result": data}
    row.status = (
        "completed" if result.status in {"completed", "needs_information", "rejected"} else result.status
    )
    s.commit()  # Board updates occur only after the result is durable.


def recover(s):
    for case in s.scalars(select(Collaboration).where(Collaboration.status.in_(ACTIVE))):
        case.status = "partial"
        case.payload = case.payload | {
            "warnings": ["Controller restarted; unconfirmed work is partial. Start a new case."]
        }
        for task in s.scalars(
            select(CollaborationTask).where(
                CollaborationTask.case_id == case.id, CollaborationTask.status == "pending"
            )
        ):
            task.status = "partial"
    s.commit()
