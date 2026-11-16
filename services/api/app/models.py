from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class ReceiptOCRUsage(Base):
    __tablename__ = "receipt_ocr_usage"
    day: Mapped[str] = mapped_column(String, primary_key=True)
    calls: Mapped[int] = mapped_column(default=0)


class Entity:
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now, onupdate=now)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    demo: Mapped[bool] = mapped_column(default=False)


class Purchase(Entity, Base):
    __tablename__ = "purchases"
    import_key: Mapped[str] = mapped_column(unique=True)


class Product(Entity, Base):
    __tablename__ = "products"
    purchase_id: Mapped[str] = mapped_column(ForeignKey("purchases.id"), index=True)
    model_number: Mapped[str | None] = mapped_column(index=True)
    upc: Mapped[str | None] = mapped_column(index=True)


class Opportunity(Entity, Base):
    __tablename__ = "opportunities"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    kind: Mapped[str]
    source_id: Mapped[str]
    official_url: Mapped[str] = mapped_column(index=True)
    __table_args__ = (UniqueConstraint("product_id", "kind", "source_id"),)


class SourceEvidence(Entity, Base):
    __tablename__ = "source_evidence"
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"))
    url: Mapped[str] = mapped_column(index=True)


class EligibilityAssessment(Entity, Base):
    __tablename__ = "eligibility_assessments"
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), unique=True)


class ClaimPacket(Entity, Base):
    __tablename__ = "claim_packets"
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), unique=True)


class AgentRun(Entity, Base):
    __tablename__ = "agent_runs"
    idempotency_key: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(default="queued", index=True)


class AuditEvent(Entity, Base):
    __tablename__ = "audit_events"
    run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id"))
    seq: Mapped[int]
    __table_args__ = (UniqueConstraint("run_id", "seq"),)


class Collaboration(Entity, Base):
    __tablename__ = "collaborations"
    product_id: Mapped[str] = mapped_column(ForeignKey("products.id"), index=True)
    idempotency_key: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(default="queued", index=True)
    current_revision: Mapped[str] = mapped_column(default="")


class CollaborationRevision(Entity, Base):
    __tablename__ = "collaboration_revisions"
    case_id: Mapped[str] = mapped_column(ForeignKey("collaborations.id"), index=True)
    revision: Mapped[str]
    __table_args__ = (UniqueConstraint("case_id", "revision"),)


class CollaborationTask(Entity, Base):
    __tablename__ = "collaboration_tasks"
    case_id: Mapped[str] = mapped_column(ForeignKey("collaborations.id"), index=True)
    revision: Mapped[str]
    deduplication_key: Mapped[str] = mapped_column(unique=True)
    seq: Mapped[int]
    status: Mapped[str] = mapped_column(default="pending")
    __table_args__ = (UniqueConstraint("case_id", "seq"),)


class CollaborationEvidence(Entity, Base):
    __tablename__ = "collaboration_evidence"
    case_id: Mapped[str] = mapped_column(ForeignKey("collaborations.id"), index=True)
    revision: Mapped[str]
    source_ref: Mapped[str]
    __table_args__ = (UniqueConstraint("case_id", "revision", "source_ref"),)


class CollaborationUsage(Base):
    __tablename__ = "collaboration_usage"
    day: Mapped[str] = mapped_column(String, primary_key=True)
    calls: Mapped[int] = mapped_column(default=0)
