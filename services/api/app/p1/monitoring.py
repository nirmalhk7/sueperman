"""Single-writer source-watch coordinator; sessions close before every await.

Checks are public reads, never agent runs or submissions. A changed/unavailable
source revokes approval; a later recovery cannot reinstate it automatically.
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import ForeignKey, UniqueConstraint, func, insert, inspect, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.collaboration import ledger
from app.matching.recall import match_recall
from app.models import (
    AgentRun,
    CaseRecord,
    ClaimPacket,
    CollaborationRun,
    EligibilityAssessment,
    Entity,
    Opportunity,
    Product,
)
from app.schemas import Condition, ProductInput, RecallRecord
from app.security.source_policy import official_cpsc

SUPPORTED_REFERENCES = frozenset({"26-792", "26-610", "25-390", "25-248"})


class WatchConflict(ValueError):
    pass


class P1Base(DeclarativeBase):
    pass


class SchemaVersion(P1Base):
    __tablename__ = "p1_schema_versions"
    version: Mapped[int] = mapped_column(primary_key=True)


class SourceWatch(Entity, P1Base):
    __tablename__ = "p1_source_watches"
    opportunity_id: Mapped[str] = mapped_column(ForeignKey(Opportunity.id, ondelete="CASCADE"), unique=True)
    enabled: Mapped[bool] = mapped_column(default=False)
    due_at: Mapped[str] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="scheduled")
    lease: Mapped[str | None] = mapped_column(default=None)


class SourceCheck(Entity, P1Base):
    __tablename__ = "p1_source_checks"
    watch_id: Mapped[str] = mapped_column(ForeignKey(SourceWatch.id, ondelete="CASCADE"), index=True)
    sequence: Mapped[int]
    __table_args__ = (UniqueConstraint("watch_id", "sequence"),)


def setup_schema(engine):
    inspector = inspect(engine)
    if inspector.has_table(SchemaVersion.__tablename__):
        with engine.connect() as connection:
            versions = connection.scalars(select(SchemaVersion.version)).all()
            if versions and versions != [1]:
                raise RuntimeError("Unsupported P1 schema version; no rebuild")
    for table in P1Base.metadata.sorted_tables:
        if inspector.has_table(table.name):
            columns = {c["name"] for c in inspector.get_columns(table.name)}
            if not set(table.columns.keys()).issubset(columns):
                raise RuntimeError(f"Incompatible P1 schema: {table.name}")
    with engine.begin() as connection:
        P1Base.metadata.create_all(connection)
        if connection.scalar(select(SchemaVersion.version)) is None:
            connection.execute(insert(SchemaVersion).values(version=1))


def utc(value):
    if value.utcoffset() is None:
        raise ValueError("UTC observation required")
    return value.astimezone(UTC)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_digest(record):
    return digest(record.model_dump(mode="json", exclude={"fetched_at", "mode"}))


def set_watch(session, opportunity_id, *, enabled, observed_at):
    observed_at = utc(observed_at)
    opportunity = session.get(Opportunity, opportunity_id)
    if opportunity is None:
        raise LookupError("Opportunity not found")
    if (opportunity.kind != "recall" or opportunity.source_id not in SUPPORTED_REFERENCES
            or not official_cpsc(opportunity.official_url)):
        raise ValueError("Only supported official recall sources can be watched")
    row = session.scalar(select(SourceWatch).where(SourceWatch.opportunity_id == opportunity_id))
    if row is not None:
        if row.enabled == enabled:
            return row
        if row.status == "checking" and enabled:
            raise WatchConflict("Wait for the in-flight source check before enabling it again")
    if enabled and (row is None or not row.enabled):
        count = session.scalar(select(func.count()).select_from(SourceWatch).where(SourceWatch.enabled.is_(True)))
        if count >= 5:
            raise ValueError("Five active source watches maximum; disable one first")
    if row is None:
        row = SourceWatch(opportunity_id=opportunity_id, enabled=enabled, due_at=observed_at.isoformat(),
                          demo=opportunity.demo, payload={"interval_hours": 24})
        session.add(row)
        session.flush()
    else:
        row.enabled = enabled
        if row.status != "checking":
            row.status = "scheduled" if enabled else "disabled"
            row.due_at = observed_at.isoformat()
    return row


def active_run(session):
    return (session.scalar(select(AgentRun.id).where(AgentRun.status.in_(["running", "queued"])))
            or session.scalar(select(CollaborationRun.id).where(CollaborationRun.status.in_(
                ["queued", "investigating", "challenging", "building"]))))


def review_required(session, opportunity, record=None):
    """A replay cannot supersede a durable official-source revocation.

    Only a later live authoritative observation can support a new review.
    Keep the watch/check history even when ordinary opportunity rows are rebuilt.
    """
    if not inspect(session.connection()).has_table(SourceWatch.__tablename__):
        return False
    watch = session.scalar(select(SourceWatch).where(SourceWatch.opportunity_id == opportunity.id))
    if watch is None:
        return False
    blocked_at = watch.payload.get("review_required_at")
    if not blocked_at:
        # Compatibility with watches created before the durable marker existed.
        checks = session.scalars(select(SourceCheck).where(SourceCheck.watch_id == watch.id)
                                 .order_by(SourceCheck.sequence.desc())).all()
        blocked_at = next((c.payload.get("observed_at") for c in checks
                           if c.payload.get("observation_status", c.payload.get("status"))
                           in {"changed", "unavailable"}), None)
        if not blocked_at and opportunity.payload.get("monitor_status"):
            return True
    if not blocked_at:
        return False
    try:
        record = record or RecallRecord.model_validate(opportunity.payload["recall"])
        return not (record.mode == "live" and record.source_type == "government"
                    and official_cpsc(record.official_url) and record.official_url == opportunity.official_url
                    and utc(record.fetched_at) > utc(datetime.fromisoformat(blocked_at)))
    except (ValueError, KeyError, TypeError):
        return True


def revoke(session, opportunity, reason, observed_at):
    watch = session.scalar(select(SourceWatch).where(SourceWatch.opportunity_id == opportunity.id))
    if watch is not None:
        watch.payload = watch.payload | {"review_required_at": utc(observed_at).isoformat(), "review_reason": reason}
    opportunity.payload = opportunity.payload | {"status": "needs_review", "monitor_status": reason,
        "matching_reasons": list(dict.fromkeys(opportunity.payload.get("matching_reasons", []) + [reason]))}
    assessment = session.scalar(select(EligibilityAssessment).where(
        EligibilityAssessment.opportunity_id == opportunity.id))
    if assessment is None:
        assessment = EligibilityAssessment(opportunity_id=opportunity.id, demo=opportunity.demo)
        session.add(assessment)
    if reason == "SOURCE_CHANGED_REVIEW_REQUIRED":
        product = session.get(Product, opportunity.product_id)
        result = match_recall(ProductInput.model_validate(product.payload["product"]),
                              RecallRecord.model_validate(opportunity.payload["recall"]))
        conditions = [c for c in result.conditions if c.name != "unsupported_source_conditions"] + [
            Condition(name="unsupported_source_conditions", expected="Review changed official source",
                      source_id=opportunity.source_id)]
    else:
        conditions = [Condition(name="official_source", expected="Fresh official source observation",
                                source_id=opportunity.source_id)]
    assessment.payload = {"outcome": "uncertain", "hard_conditions": [c.model_dump(mode="json") for c in conditions],
        "missing_fields": [c.name for c in conditions if c.status == "unknown"],
        "reasons": [reason], "performed_by": "source_monitor", "evaluated_at": observed_at.isoformat()}
    for packet in session.scalars(select(ClaimPacket).where(ClaimPacket.opportunity_id == opportunity.id)):
        packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None,
            "reviewed_at": None, "source_review_required": True}
    for case in session.scalars(select(CaseRecord).where(CaseRecord.product_id == opportunity.product_id)):
        previous = ledger.current_revision(session, case)
        if previous:
            ledger.revise(session, case, previous.payload | {"evidence_hashes": [digest({
                "source": opportunity.source_id, "reason": reason, "observed_at": observed_at.isoformat()})]})


def recover_interrupted(session, observed_at):
    for watch in session.scalars(select(SourceWatch).where(SourceWatch.status == "checking")):
        watch.enabled, watch.status, watch.lease = False, "interrupted", None
        watch.payload = watch.payload | {"reason": "SOURCE_CHECK_INTERRUPTED"}
        opportunity = session.get(Opportunity, watch.opportunity_id)
        revoke(session, opportunity, "SOURCE_CHECK_INTERRUPTED", utc(observed_at))


@dataclass(frozen=True)
class CheckInput:
    watch_id: str
    opportunity_id: str
    reference: str
    before_json: str
    product_digest: str
    lease: str


def claim_due(factory, observed_at):
    with factory.begin() as session:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
        if active_run(session) or session.scalar(select(SourceWatch.id).where(SourceWatch.status == "checking")):
            return None
        watch = session.scalar(select(SourceWatch).where(SourceWatch.enabled.is_(True),
            SourceWatch.due_at <= observed_at.isoformat()).order_by(SourceWatch.due_at, SourceWatch.id))
        if watch is None:
            return None
        opportunity = session.get(Opportunity, watch.opportunity_id)
        product = session.get(Product, opportunity.product_id)
        watch.status, watch.lease = "checking", str(uuid4())
        # Intent and next due are durable before the request. Failure never causes an immediate retry.
        watch.due_at = (observed_at + timedelta(hours=24)).isoformat()
        return CheckInput(watch.id, opportunity.id, opportunity.source_id,
                          json.dumps(opportunity.payload["recall"]), digest(product.payload), watch.lease)


async def check_due(factory, checker, *, clock=None, timeout_seconds=10):
    clock = clock or (lambda: datetime.now(UTC))
    results = []
    for _ in range(5):
        observed_at = utc(clock())
        context = claim_due(factory, observed_at)
        if context is None:
            break
        before = RecallRecord.model_validate_json(context.before_json)
        after = None
        try:
            async with asyncio.timeout(min(timeout_seconds, 10)):
                value = await checker(context.reference)
            after = RecallRecord.model_validate(value.model_dump(mode="json"))
            if (after.reference != context.reference or after.official_url != before.official_url
                    or not official_cpsc(after.official_url) or after.source_type != "government"):
                raise ValueError("Wrong source")
            status = "unchanged" if source_digest(after) == source_digest(before) else "changed"
        except Exception:  # noqa: BLE001 — sanitize provider failures at the worker boundary
            status, after = "unavailable", None
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            watch = session.get(SourceWatch, context.watch_id)
            if watch is None or watch.lease != context.lease:
                continue
            opportunity = session.get(Opportunity, context.opportunity_id)
            product = session.get(Product, opportunity.product_id)
            observation_status = status
            if (not watch.enabled or active_run(session) or digest(product.payload) != context.product_digest
                    or source_digest(RecallRecord.model_validate(opportunity.payload["recall"])) != source_digest(before)):
                status = "stale"
                if observation_status in {"changed", "unavailable"}:
                    revoke(session, opportunity, "SOURCE_CHECK_SUPERSEDED_REVIEW_REQUIRED", utc(clock()))
            if status == "changed":
                assert after is not None
                opportunity.payload = opportunity.payload | {"recall": after.model_dump(mode="json")}
                revoke(session, opportunity, "SOURCE_CHANGED_REVIEW_REQUIRED", utc(clock()))
            elif status == "unavailable":
                revoke(session, opportunity, "SOURCE_MONITOR_UNAVAILABLE", utc(clock()))
            watch.status, watch.lease = status, None
            watch.payload = watch.payload | {"last_checked_at": utc(clock()).isoformat(), "last_result": status}
            sequence = len(session.scalars(select(SourceCheck).where(SourceCheck.watch_id == watch.id)).all()) + 1
            session.add(SourceCheck(watch_id=watch.id, sequence=sequence, demo=watch.demo, payload={
                "status": status, "observation_status": observation_status, "observed_at": utc(clock()).isoformat(),
                "before_digest": source_digest(before), "after_digest": source_digest(after) if after else None,
                "before": before.model_dump(mode="json"), "after": after.model_dump(mode="json") if after else None,
            }))
        results.append(status)
    return results


async def fetch_public(reference):
    from app.providers.cpsc import CPSCRecallSource
    from app.providers.errors import ProviderUnavailable
    from app.schemas import ProductInput

    queries = {"26-792": "NEWDERY", "26-610": "Flaunt", "25-390": "iStore", "25-248": "Baseus"}
    if reference not in queries:
        raise ValueError("Unsupported public source reference")
    source = CPSCRecallSource(reviewed_notices=True)
    rows = await source.search(ProductInput(product_name="Power bank", brand=queries[reference]))
    matches = [row for row in rows if row.reference == reference]
    if len(matches) != 1 or source.truncated:
        raise ProviderUnavailable("Watched public source missing, ambiguous or truncated")
    return matches[0]


async def watch_loop(factory, stopped, *, checker=None, clock=None, poll_seconds=60):
    if poll_seconds <= 0:
        raise ValueError("Positive scheduler interval required")
    while not stopped.is_set():
        try:
            await asyncio.wait_for(stopped.wait(), timeout=poll_seconds)
        except TimeoutError:
            await check_due(factory, checker or fetch_public, clock=clock)
