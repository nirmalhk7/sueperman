"""Four bounded actors and a pure manager reducer. No sessions or provider SDKs."""

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from functools import partial
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID, uuid5

from app.claims.compose import compose
from app.config import ROOT
from app.diwali.message_schema import (
    BuildReport,
    ComparedIdentifiers,
    FollowUpReport,
    InputDigests,
    Message,
    ResearchReport,
    ReviewReport,
    TaskFailed,
    UnsignedDraft,
    validate_delivery,
    validate_sources,
)
from app.matching.normalize import normalize_model, normalize_text
from app.matching.recall import match_recall
from app.matching.settlement import match_settlement
from app.schemas import ProductInput, RecallRecord, SettlementRecord
from app.security.source_policy import official_cpsc


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class CaseInput:
    run_id: UUID
    case_id: UUID
    product_ref: str
    product_json: str
    records_json: tuple[str, ...]
    task_ids: tuple[UUID, ...]
    started_at: datetime
    settlement_json: str = ""
    max_followups: int = 1

    @property
    def product(self):
        return ProductInput.model_validate_json(self.product_json)

    @property
    def records(self):
        return tuple(RecallRecord.model_validate_json(s) for s in self.records_json)

    @property
    def sources(self):
        return {f"cpsc:{r.reference}:{digest(r.model_dump(mode='json'))}": r for r in self.records}

    @property
    def snapshot_registry(self):
        return {ref: {"run_id": str(self.run_id), "digest": digest(record.model_dump(mode="json")),
                      "record": record.model_dump(mode="json")} for ref, record in self.sources.items()}

    @property
    def input_digests(self):
        return InputDigests(purchase=digest(json.loads(self.product_json)),
                            evidence=digest([json.loads(s) for s in self.records_json]))


@dataclass(frozen=True)
class Start:
    pass


@dataclass(frozen=True)
class Finalized:
    """Coordinator acknowledgement, only after the domain transaction commits."""


@dataclass(frozen=True)
class Command:
    message: Message | None = None
    audit: str | None = None
    finalize: bool = False


@dataclass(frozen=True)
class CaseState:
    context: CaseInput
    phase: str = "NEW"
    outcome: str | None = None
    revision: int = 0
    next_task: int = 0
    pending_task: UUID | None = None
    accepted: tuple[tuple[UUID, str], ...] = ()
    completed_tasks: tuple[UUID, ...] = ()
    source_refs: tuple[str, ...] = ()
    followups: int = 0
    followup_fields: tuple[str, ...] = ()
    draft: UnsignedDraft | None = None
    compared_identifiers: ComparedIdentifiers | None = None
    challenge_code: str = "NONE"
    question_field: str | None = None
    notes: tuple[str, ...] = ()
    failure: str | None = None


def request(state, kind, payload, phase, refs=(), cause=None, *, observed_at=None):
    context = state.context
    issued_at = observed_at or context.started_at
    if issued_at < context.started_at:
        raise ValueError("Task time precedes case start")
    if state.next_task >= len(context.task_ids):
        raise ValueError("Task budget exhausted")
    task = context.task_ids[state.next_task]
    revision = state.revision + 1
    actor = {"ResearchRequested": "researcher", "ReviewRequested": "skeptic",
             "FollowUpRequested": "researcher", "BuildRequested": "builder"}[kind]
    message = Message.model_validate({
        "schema_version": 1, "message_id": uuid5(task, kind), "run_id": context.run_id,
        "case_id": context.case_id, "task_id": task, "correlation_id": context.case_id,
        "causation_id": cause or context.case_id, "expected_case_revision": revision,
        "sender": "manager", "recipient": actor, "type": kind,
        "sent_at": issued_at, "deadline_at": issued_at + timedelta(seconds=10),
        "source_refs": list(refs), "payload": payload,
    })
    return replace(state, phase=phase, revision=revision, pending_task=task,
                   next_task=state.next_task + 1), (Command(message=message),)


def review_payload(context, refs):
    record = context.sources[refs[0]]
    product = context.product
    result = match_recall(product, record)
    model_condition = next(c for c in result.conditions if c.name == "model_number")
    missing_purchase = [c.name for c in result.conditions
                        if c.status == "unknown" and getattr(product, c.name, None) is None]
    # An absent public affected-model list is not a missing private purchase model.
    public_fields = ["affected_models"] if product.model_number and not record.models else []
    challenge = ("MODEL_MISMATCH" if result.status == "rejected" and model_condition.status == "false"
                 else "CONDITION_FAILED" if result.status == "rejected"
                 else "MISSING_PUBLIC_FACT" if public_fields
                 else "MISSING_PURCHASE_FACT" if missing_purchase else "NONE")
    return ReviewReport.model_validate({
        "rule_result": result.status, "conditions": [c.model_dump(mode="json") for c in result.conditions],
        "compared_identifiers": {"purchase_model": product.model_number, "source_models": record.models},
        "challenge_code": challenge, "review_note": "", "requested_fields": public_fields,
    })


def builder_payload(context, refs):
    record = context.sources[refs[0]]
    if match_recall(context.product, record).status != "verified_match":
        raise ValueError("Builder requires authoritative verified assessment")
    fields = {"product_name": context.product.product_name, "brand": context.product.brand,
              "model_number": context.product.model_number}
    for condition in record.conditions:
        if condition.name in ProductInput.model_fields and condition.name != "order_reference_redacted":
            fields[condition.name] = getattr(context.product, condition.name)
    packet = compose(ProductInput.model_validate(fields), record)
    return BuildReport.model_validate({
        "draft": {"markdown": packet["markdown"], "status": "ready_for_review", "approved_at": None},
        "view": {"purchase_model": context.product.model_number, "source_models": record.models,
                 "source_ref": refs[0]},
        "input_digests": context.input_digests.model_dump(),
    })


def research_actor(request_message: Message, context: CaseInput) -> Message:
    if request_message.type == "FollowUpRequested":
        return reply(request_message, "FollowUpReport",
                     {"evidence_refs": [], "unavailable_reason": "SOURCE_UNAVAILABLE"},
                     list(request_message.source_refs))
    candidates: dict[str, str] = {}
    for ref, record in context.sources.items():
        product = context.product
        if (normalize_text(product.brand) == normalize_text(record.brand)
                or normalize_text(record.family) in normalize_text(product.product_name)
                or normalize_model(product.model_number) in [normalize_model(m) for m in record.models]):
            parts = urlsplit(record.official_url)
            if (not official_cpsc(record.official_url) or parts.query or parts.fragment
                    or record.source_type != "government"
                    or record.reference != "26-792"
                    or record.models not in ([], ["ZHX-PB22"])
                    or record.excerpt != "This recall involves NEWDERY power banks with model number ZHX-PB22."):
                return failure_reply(request_message, "INVALID_RESULT")
            facts = record.model_dump(mode="json", exclude={"fetched_at"})
            fingerprint = digest(facts)
            previous = candidates.get(fingerprint)
            if previous is None or record.fetched_at > context.sources[previous].fetched_at:
                candidates[fingerprint] = ref
    refs = [candidates[key] for key in sorted(candidates)][:10]
    return reply(request_message, "ResearchReport",
                 {"candidate_refs": refs, "coverage": "supported_scope", "truncated": len(candidates) > 10}, refs)


def skeptic_actor(request_message: Message, context: CaseInput) -> Message:
    refs = list(request_message.source_refs)
    return reply(request_message, "ReviewReport", review_payload(context, refs).model_dump(mode="json"), refs)


def builder_actor(request_message: Message, context: CaseInput) -> Message:
    refs = list(request_message.source_refs)
    return reply(request_message, "BuildReport", builder_payload(context, refs).model_dump(mode="json"), refs)


def actor_reply(request_message: Message, context: CaseInput) -> Message:
    """Dispatch separate immutable-input handlers; manager alone consumes results."""
    handlers = {"ResearchRequested": research_actor, "FollowUpRequested": research_actor,
                "ReviewRequested": skeptic_actor, "BuildRequested": builder_actor}
    if request_message.type not in handlers:
        raise ValueError("Actor cannot handle this request")
    return handlers[request_message.type](request_message, context)


def reply(request_message, kind, payload, refs):
    data = request_message.model_dump(mode="json")
    data.update(message_id=str(uuid5(request_message.message_id, kind)),
                causation_id=str(request_message.message_id), sender=request_message.recipient,
                recipient="manager", type=kind, source_refs=refs, payload=payload)
    return Message.model_validate(data)


def failure_reply(request_message, reason):
    return reply(request_message, "TaskFailed", {"reason_code": reason, "retryable": False}, [])


def reduce_case(state: CaseState, accepted_message: Message | Start | Finalized, *, observed_at=None):
    """Return prospective state and commands, without I/O or implicit time/ID reads."""
    schedule = partial(request, observed_at=observed_at)
    if isinstance(accepted_message, Start):
        if state.phase != "NEW":
            raise ValueError("Case already started")
        return schedule(state, "ResearchRequested", {"product_ref": state.context.product_ref}, "RESEARCHING")
    if isinstance(accepted_message, Finalized):
        if state.phase != "FINALIZING":
            raise ValueError("No pending finalization")
        return replace(state, phase="DONE"), ()
    message = Message.model_validate(accepted_message.model_dump(mode="json"))
    fingerprint = digest(message.model_dump(mode="json"))
    seen = dict(state.accepted)
    if message.message_id in seen:
        if seen[message.message_id] != fingerprint:
            raise ValueError("Conflicting message ID reuse")
        return state, ()
    if state.phase == "DONE" or message.task_id in state.completed_tasks:
        return state, ()
    expected = {"RESEARCHING": "ResearchReport", "REVIEWING": "ReviewReport",
                "FOLLOWUP": "FollowUpReport", "BUILDING": "BuildReport"}
    assigned = {"RESEARCHING": "researcher", "REVIEWING": "skeptic", "FOLLOWUP": "researcher",
                "BUILDING": "builder"}
    if message.sender != assigned.get(state.phase):
        raise ValueError("Result did not come from assigned actor")
    if (message.run_id != state.context.run_id or message.case_id != state.context.case_id
            or message.task_id != state.pending_task or message.expected_case_revision != state.revision
            or message.type not in {expected.get(state.phase), "TaskFailed"}):
        raise ValueError("Wrong task, phase, case or revision")
    refs = set(state.context.sources)
    if not set(message.source_refs).issubset(refs):
        raise ValueError("Unknown source reference")
    if message.type in {"ReviewReport", "BuildReport"} and set(message.source_refs) != set(state.source_refs):
        raise ValueError("Result must cite assigned snapshot")
    state = replace(state, accepted=(*state.accepted, (message.message_id, fingerprint)),
                    completed_tasks=(*state.completed_tasks, message.task_id))
    if isinstance(message.payload, TaskFailed):
        return replace(state, phase="DONE", failure=message.payload.reason_code,
                       revision=state.revision + 1), (Command(audit="RunFailed", finalize=True),)
    if isinstance(message.payload, ResearchReport):
        if message.payload.coverage == "unavailable":
            return replace(state, phase="DONE", failure="SOURCE_UNAVAILABLE",
                           revision=state.revision + 1), (Command(audit="RunFailed", finalize=True),)
        candidates = message.payload.candidate_refs
        if not candidates:
            outcome = "no_match"
            notes: tuple[str, ...] = ()
            if state.context.settlement_json:
                rules = SettlementRecord.model_validate_json(state.context.settlement_json)
                result = match_settlement(state.context.product, rules, date(2026, 11, 13))
                if result.status == "eligible_candidate":
                    outcome, notes = "simulated_settlement", tuple(result.reasons)
            return replace(state, phase="DONE", outcome=outcome, notes=notes,
                           revision=state.revision + 1), (Command(audit="CaseFinalized", finalize=True),)
        state = replace(state, source_refs=tuple(candidates))
        if len(candidates) != 1 or message.payload.truncated:
            return replace(state, phase="DONE", outcome="needs_review", revision=state.revision + 1), (
                Command(audit="CaseFinalized", finalize=True),)
        return schedule(state, "ReviewRequested", {"product_ref": state.context.product_ref,
                       "evidence_refs": candidates}, "REVIEWING", candidates, message.message_id)
    if isinstance(message.payload, ReviewReport):
        review = message.payload
        authoritative = review_payload(state.context, state.source_refs)
        for field in ("rule_result", "conditions", "compared_identifiers", "challenge_code"):
            if getattr(review, field) != getattr(authoritative, field):
                raise ValueError("Review differs from authoritative matcher")
        state = replace(state, compared_identifiers=review.compared_identifiers,
                        challenge_code=review.challenge_code)
        if review.rule_result == "rejected":
            return replace(state, phase="DONE", outcome="rejected", revision=state.revision + 1), (
                Command(audit="ChallengeRaised"), Command(audit="CaseFinalized", finalize=True))
        if not state.context.product.model_number:
            return replace(state, phase="DONE", outcome="needs_review", question_field="model_number",
                           revision=state.revision + 1), (Command(audit="CaseFinalized", finalize=True),)
        if review.rule_result == "needs_review":
            allowed = [f for f in review.requested_fields if f in authoritative.requested_fields]
            if allowed and state.followups < state.context.max_followups:
                return schedule(replace(state, followups=1, followup_fields=tuple(allowed)), "FollowUpRequested",
                               {"requested_fields": allowed, "evidence_refs": list(state.source_refs)},
                               "FOLLOWUP", state.source_refs, message.message_id)
            return replace(state, phase="DONE", outcome="needs_review", revision=state.revision + 1), (
                Command(audit="CaseFinalized", finalize=True),)
        return schedule(state, "BuildRequested", {"rule_result": "verified_match",
                       "evidence_refs": list(state.source_refs),
                       "input_digests": state.context.input_digests.model_dump()}, "BUILDING",
                       state.source_refs, message.message_id)
    if isinstance(message.payload, FollowUpReport):
        new_refs = message.payload.evidence_refs
        if new_refs:
            original = state.context.sources[state.source_refs[0]]
            allowed_changes = {"affected_models": "models", "remedy_instructions": "instructions",
                               "proof_requirements": "required_documents", "safety_instructions": "safety_instructions"}
            fields = {allowed_changes[f] for f in state.followup_fields} | {"fetched_at"}
            for ref in new_refs:
                record = state.context.sources[ref]
                before, after = original.model_dump(mode="json"), record.model_dump(mode="json")
                if (record.models not in ([], ["ZHX-PB22"])
                        or any(before[k] != after[k] for k in before if k not in fields)):
                    raise ValueError("Follow-up changed unrequested or untrusted source facts")
            state = replace(state, source_refs=tuple(new_refs))
        return schedule(state, "ReviewRequested", {"product_ref": state.context.product_ref,
                       "evidence_refs": list(state.source_refs)}, "REVIEWING", state.source_refs,
                       message.message_id)
    if not isinstance(message.payload, BuildReport):
        raise TypeError("Expected build result")
    if message.payload != builder_payload(state.context, state.source_refs):
        raise ValueError("Build report differs from current authoritative inputs")
    return replace(state, phase="FINALIZING", outcome="verified_match", draft=message.payload.draft,
                   revision=state.revision + 1), (Command(audit="PacketPrepared", finalize=True),)


class LocalTransport:
    mode: Literal["local"] = "local"
    def __init__(self):
        self.identities = {role: f"local-test-{role}" for role in ("manager", "researcher", "skeptic", "builder")}
        self.inboxes: dict[str, dict[UUID, tuple[str, Message]]] = {role: {} for role in self.identities}

    def exchange(self, message, context):
        message = Message.model_validate_json(message.model_dump_json())
        validate_delivery(message, self.identities[message.sender], self.identities[message.recipient],
                          self.identities)
        if message.run_id != context.run_id or message.case_id != context.case_id:
            raise ValueError("Request belongs to another frozen case")
        snapshots = context.snapshot_registry
        validate_sources(message, snapshots, {ref: snapshot["digest"] for ref, snapshot in snapshots.items()})
        fingerprint = digest({"message": message.model_dump(mode="json"),
                              "inputs": context.input_digests.model_dump()})
        inbox = self.inboxes[message.recipient]
        old = inbox.get(message.message_id)
        if old:
            if old[0] != fingerprint:
                raise ValueError("Conflicting request ID reuse")
            return Message.model_validate_json(old[1].model_dump_json())
        result = actor_reply(message, context)
        inbox[message.message_id] = (fingerprint, result)
        self.inboxes["manager"][result.message_id] = (digest(result.model_dump(mode="json")), result)
        return Message.model_validate_json(result.model_dump_json())


class RecordedTransport(LocalTransport):
    """Read-only captured LOCAL TEST messages; never BAND proof."""

    def __init__(self, messages: tuple[str, ...]):
        super().__init__()
        self.messages = tuple(Message.model_validate_json(m) for m in messages)
        self.position = 0

    def exchange(self, message, context):
        if self.messages[self.position] != message:
            raise ValueError("Recorded request does not match current inputs")
        result = self.messages[self.position + 1]
        self.position += 2
        return result


@dataclass(frozen=True)
class LocalResult(CaseState):
    messages: tuple[Message, ...] = ()
    transport: str = "local"
    source: str = "recorded"
    identities: dict | None = None


def run_local(context, transport=None):
    """G2 driver. G3 replaces immediate finalization with a coordinator transaction."""
    if not context.settlement_json:
        context = replace(context, settlement_json=(ROOT / "demo/settlement_fixture.json").read_text())
    transport = transport or LocalTransport()
    state, commands = reduce_case(CaseState(context), Start())
    trace: list[Message] = []
    while commands:
        outgoing = next((c.message for c in commands if c.message), None)
        if outgoing is None:
            break
        incoming = transport.exchange(outgoing, context)
        validate_delivery(incoming, transport.identities[incoming.sender], transport.identities[incoming.recipient],
                          transport.identities)
        trace.extend((outgoing, incoming))
        if len(trace) > 12:
            raise ValueError("Application message budget exhausted")
        state, commands = reduce_case(state, incoming)
    if state.phase == "FINALIZING":
        state, _ = reduce_case(state, Finalized())
    return LocalResult(**vars(state), messages=tuple(trace), identities=dict(transport.identities))
