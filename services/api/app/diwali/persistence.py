"""Explicit additive schema and transaction facade. Nothing here commits internally."""

import hashlib
from datetime import date
from urllib.parse import urlsplit

from sqlalchemy import ForeignKey, UniqueConstraint, insert, inspect, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.claims.compose import compose
from app.diwali.core import digest
from app.matching.recall import match_recall
from app.matching.settlement import match_settlement
from app.models import (
    AgentRun,
    AuditEvent,
    ClaimPacket,
    EligibilityAssessment,
    Entity,
    Opportunity,
    Product,
    SourceEvidence,
    now,
)
from app.schemas import ProductInput, RecallRecord, SettlementRecord


class DiwaliBase(DeclarativeBase):
    pass


class SchemaVersion(DiwaliBase):
    __tablename__ = "diwali_schema_versions"
    version: Mapped[int] = mapped_column(primary_key=True)


class CaseRow(Entity, DiwaliBase):
    __tablename__ = "diwali_cases"
    run_id: Mapped[str] = mapped_column(ForeignKey(AgentRun.id, ondelete="CASCADE"))
    product_id: Mapped[str] = mapped_column(ForeignKey(Product.id, ondelete="CASCADE"))
    phase: Mapped[str]
    revision: Mapped[int]
    __table_args__ = (UniqueConstraint("run_id", "product_id"),)


class MessageRow(Entity, DiwaliBase):
    __tablename__ = "agent_messages"
    run_id: Mapped[str] = mapped_column(ForeignKey(AgentRun.id, ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(ForeignKey(CaseRow.id, ondelete="CASCADE"))
    task_id: Mapped[str]
    seq: Mapped[int | None]
    digest: Mapped[str]
    delivery: Mapped[str]
    __table_args__ = (UniqueConstraint("run_id", "seq"),)


class TaskRow(Entity, DiwaliBase):
    __tablename__ = "agent_tasks"
    run_id: Mapped[str] = mapped_column(ForeignKey(AgentRun.id, ondelete="CASCADE"))
    case_id: Mapped[str] = mapped_column(ForeignKey(CaseRow.id, ondelete="CASCADE"))
    state: Mapped[str]


class InvocationRow(Entity, DiwaliBase):
    __tablename__ = "provider_invocations"
    task_id: Mapped[str] = mapped_column(ForeignKey(TaskRow.id, ondelete="CASCADE"))
    provider: Mapped[str]
    mode: Mapped[str]


def setup_schema(engine):
    """Called explicitly at app startup, never by module import or a request."""
    inspector = inspect(engine)
    if inspector.has_table(SchemaVersion.__tablename__):
        with engine.connect() as connection:
            versions = connection.scalars(select(SchemaVersion.version)).all()
            if versions and versions != [1]:
                raise RuntimeError("Unsupported Diwali schema version; no automatic rebuild")
    for table in DiwaliBase.metadata.sorted_tables:
        if inspector.has_table(table.name):
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            if not set(table.columns.keys()).issubset(existing):
                raise RuntimeError(f"Incompatible Diwali schema: {table.name}")
    with engine.begin() as connection:
        DiwaliBase.metadata.create_all(connection)
        if connection.scalar(select(SchemaVersion.version)) is None:
            connection.execute(insert(SchemaVersion).values(version=1))


def audit(session, run, stage, refs=()):
    session.flush()
    seq = len(session.scalars(select(AuditEvent).where(AuditEvent.run_id == run.id)).all()) + 1
    session.add(AuditEvent(run_id=run.id, seq=seq, demo=run.demo, payload={
        "seq": seq, "stage": stage, "action": stage.lower(), "outcome": "ok", "timestamp": now(),
        "duration_ms": None, "provider": "local", "source_refs": list(refs), "redacted_details": {},
    }))


def stage_finalization(session, run_id, product_id, state):
    """Stage domain rows plus final case/audit state in the caller's transaction."""
    run = session.get(AgentRun, run_id)
    entity = session.get(Product, product_id)
    if str(state.context.run_id) != run_id or state.context.product_ref != product_id:
        raise ValueError("Finalization references another run or product")
    case = session.scalar(select(CaseRow).where(CaseRow.run_id == run_id, CaseRow.product_id == product_id))
    if case is not None and case.phase == "DONE":
        identifier = case.payload.get("opportunity_id")
        return session.get(Opportunity, identifier) if identifier else None
    if case is None:
        case = CaseRow(id=str(state.context.case_id), run_id=run_id, product_id=product_id,
                       phase="FINALIZING", revision=state.revision, demo=True, payload={})
        session.add(case)
    frozen = {"frozen_purchase": state.context.product.model_dump(mode="json"),
              "frozen_evidence": [r.model_dump(mode="json") for r in state.context.records],
              "source_snapshots": state.context.snapshot_registry,
              "input_digests": state.context.input_digests.model_dump(), "outcome": state.outcome,
              "active_evidence_digest": digest(state.context.sources[state.source_refs[0]].model_dump(mode="json"))
              if state.source_refs else None,
              "question_field": state.question_field, "failure": state.failure,
              "challenge_code": state.challenge_code}
    current = ProductInput.model_validate(entity.payload["product"])
    if digest(current.model_dump(mode="json")) != state.context.input_digests.purchase:
        case.payload = case.payload | frozen | {"outcome": "needs_review", "failure": "STALE_INPUT"}
        case.phase = "DONE"
        return None
    opportunity = None
    if len(state.source_refs) > 1 and state.outcome == "needs_review":
        # Ambiguity is a valid analysis outcome; do not choose a convenient candidate.
        for old in session.scalars(select(Opportunity).where(
                Opportunity.product_id == product_id, Opportunity.kind == "recall")):
            old.payload = old.payload | {"status": "needs_review"}
            packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == old.id))
            if packet:
                packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None}
    elif state.source_refs and state.outcome in {"verified_match", "rejected", "needs_review"}:
        record = state.context.sources[state.source_refs[0]]
        result = match_recall(current, record)
        if result.status != state.outcome:
            raise ValueError("Final outcome differs from authoritative matcher")
        opportunity = stage_recall(session, entity, current, record, result, state)
    elif state.outcome == "simulated_settlement":
        opportunity = stage_settlement(session, entity, current, state.context.settlement_json)
    if opportunity is not None:
        session.flush()
        run.payload = run.payload | {"opportunities": list(dict.fromkeys(
            [*run.payload.get("opportunities", []), opportunity.id]))}
    case.payload = case.payload | frozen | {"opportunity_id": opportunity.id if opportunity else None}
    case.phase, case.revision = "DONE", state.revision
    if state.challenge_code == "MODEL_MISMATCH":
        audit(session, run, "ChallengeRaised", state.source_refs)
    audit(session, run, "CaseFinalized", state.source_refs)
    return opportunity


def stage_recall(session, entity, product, recall, result, state):
    opp = session.scalar(select(Opportunity).where(
        Opportunity.product_id == entity.id, Opportunity.kind == "recall", Opportunity.source_id == recall.reference))
    if opp is None:
        opp = Opportunity(product_id=entity.id, kind="recall", source_id=recall.reference,
                          official_url=recall.official_url, demo=True, payload={})
        session.add(opp)
        session.flush()
    opp.payload = {
        "product_id": entity.id, "kind": "recall", "title": recall.title, "status": result.status,
        "official_url": recall.official_url, "source_id": recall.reference,
        "matching_reasons": result.reasons,
        "contrary_evidence": [c.model_dump(mode="json") for c in result.conditions if c.status == "false"],
        "source_observed_at": recall.fetched_at.isoformat(), "simulated": False, "mode": recall.mode,
        "remedy_kind": recall.remedy_kind, "recall": recall.model_dump(mode="json"),
    }
    for old in session.scalars(select(SourceEvidence).where(SourceEvidence.opportunity_id == opp.id)):
        session.delete(old)
    session.add(SourceEvidence(opportunity_id=opp.id, url=recall.official_url, demo=True, payload={
        "url": recall.official_url, "domain": urlsplit(recall.official_url).hostname, "publisher": recall.publisher,
        "source_type": "government", "title": recall.title, "fetched_at": recall.fetched_at.isoformat(),
        "quoted_excerpt": recall.excerpt, "content_sha256": hashlib.sha256(recall.excerpt.encode()).hexdigest(),
        "extracted_facts": recall.model_dump(mode="json"), "authoritative_for": ["model", "remedy", "safety"],
    }))
    assessment = session.scalar(select(EligibilityAssessment).where(EligibilityAssessment.opportunity_id == opp.id))
    if assessment is None:
        assessment = EligibilityAssessment(opportunity_id=opp.id, demo=True)
        session.add(assessment)
    assessment.payload = {
        "outcome": {"verified_match": "eligible_candidate", "rejected": "ineligible"}.get(result.status, "uncertain"),
        "hard_conditions": [c.model_dump(mode="json") for c in result.conditions],
        "missing_fields": [c.name for c in result.conditions if c.status == "unknown"],
        "reasons": result.reasons, "performed_by": "deterministic", "evaluated_at": now(),
    }
    packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == opp.id))
    if result.status == "verified_match":
        if state.draft is None:
            raise ValueError("Verified case requires a consumed Builder draft")
        content = compose(product, recall) | {"generated_at": now(), "diwali_case_id": str(state.context.case_id),
                                            "markdown": state.draft.markdown}
        if packet is None:
            session.add(ClaimPacket(opportunity_id=opp.id, demo=True, payload=content))
        else:
            packet.payload = content
    elif packet is not None:
        packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None}
    return opp


def stage_settlement(session, entity, product, rules_json):
    rules = SettlementRecord.model_validate_json(rules_json)
    result = match_settlement(product, rules, date(2026, 11, 13))
    opp = session.scalar(select(Opportunity).where(Opportunity.product_id == entity.id, Opportunity.kind == "settlement"))
    if opp is not None:
        return opp
    opp = Opportunity(product_id=entity.id, kind="settlement", source_id=rules.source_url,
                      official_url=rules.source_url, demo=True, payload={
        "product_id": entity.id, "kind": "settlement", "title": rules.title, "status": result.status,
        "matching_reasons": result.reasons, "simulated": True, "mode": "fixture", "source_id": rules.source_url,
        "official_url": rules.source_url, "source_observed_at": rules.fetched_at.isoformat(),
        "deadline_at": rules.deadline.isoformat(), "remedy_kind": "unknown", "evaluated_as_of": "2026-11-13",
    })
    session.add(opp)
    session.flush()
    session.add(SourceEvidence(opportunity_id=opp.id, url=rules.source_url, demo=True, payload={
        "url": rules.source_url, "publisher": "Synthetic demo fixture", "source_type": "fixture",
        "fetched_at": rules.fetched_at.isoformat(), "quoted_excerpt": "SIMULATED CASE — NO REAL CLAIM AVAILABLE",
        "content_sha256": hashlib.sha256(rules.model_dump_json().encode()).hexdigest(),
    }))
    session.add(EligibilityAssessment(opportunity_id=opp.id, demo=True, payload={
        "outcome": result.status, "hard_conditions": [c.model_dump(mode="json") for c in result.conditions],
        "missing_fields": [], "reasons": result.reasons, "performed_by": "deterministic", "evaluated_at": now(),
    }))
    return opp


def invalidate_stale(session, packet_id):
    packet = session.get(ClaimPacket, packet_id)
    case_id = packet.payload.get("diwali_case_id")
    if not case_id:
        return False
    case = session.get(CaseRow, case_id)
    product = session.get(Product, case.product_id)
    opportunity = session.get(Opportunity, packet.opportunity_id)
    current = ProductInput.model_validate(product.payload["product"])
    record = RecallRecord.model_validate(opportunity.payload["recall"])
    stale = (digest(current.model_dump(mode="json")) != case.payload["input_digests"]["purchase"]
             or digest(record.model_dump(mode="json")) != case.payload["active_evidence_digest"])
    sources = session.scalars(select(SourceEvidence).where(SourceEvidence.opportunity_id == opportunity.id)).all()
    stale = stale or not sources or any(
        source.url != record.official_url or source.payload.get("quoted_excerpt") != record.excerpt
        or source.payload.get("content_sha256") != hashlib.sha256(record.excerpt.encode()).hexdigest()
        for source in sources)
    if stale:
        packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None}
        opportunity.payload = opportunity.payload | {"status": "needs_review"}
    return stale


def recover_interrupted(session):
    for run in session.scalars(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))):
        if run.payload.get("collaboration_mode") not in {"local", "band"}:
            continue
        cases = session.scalars(select(CaseRow).where(CaseRow.run_id == run.id)).all()
        run.status = "partial" if surviving_results(session, run.id) else "failed"
        run.payload = run.payload | {"warnings": ["RESTART: cancelled; explicit new run required"]}
        for task in session.scalars(select(TaskRow).where(TaskRow.run_id == run.id, TaskRow.state != "consumed")):
            task.state = "cancelled"
        for case in cases:
            if case.phase != "DONE":
                case.phase = "DONE"
                case.payload = case.payload | {"failure": "RESTART"}


def surviving_results(session, run_id):
    return any(row.payload.get("envelope", {}).get("type") in {
        "ResearchReport", "ReviewReport", "FollowUpReport", "BuildReport"}
        for row in session.scalars(select(MessageRow).where(
            MessageRow.run_id == run_id, MessageRow.delivery == "consumed")))
