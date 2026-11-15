from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

RemedyKind = Literal["refund", "repair", "replacement", "credit", "other", "unknown"]


class ProductInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_name: str = Field(min_length=1, max_length=500)
    brand: str | None = None
    model_number: str | None = None
    upc: str | None = None
    serial_prefix: str | None = None
    batch: str | None = None
    region: str | None = None
    date_purchased: date | None = None
    merchant: str | None = None
    order_reference_redacted: str | None = None
    extraction_confidence: float = Field(default=1, ge=0, le=1)
    user_confirmed_identifiers: bool = False
    suggested_identifiers: dict[str, str] = Field(default_factory=dict)


class Condition(BaseModel):
    name: str
    expected: Any
    observed: Any = None
    status: Literal["true", "false", "unknown"] = "unknown"
    source_id: str | None = None


class RecallRecord(BaseModel):
    reference: str
    title: str
    brand: str
    family: str
    models: list[str] = Field(default_factory=list)
    official_url: str
    fetched_at: datetime
    source_type: str
    publisher: str
    excerpt: str
    remedy_kind: RemedyKind = "unknown"
    instructions: str = "Remedy instructions unknown; consult the official notice."
    safety_instructions: str | None = None
    contact_url: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    conditions: list[Condition] = Field(default_factory=list)
    mode: Literal["replay", "live"] = "replay"


class MatchResult(BaseModel):
    status: str
    conditions: list[Condition] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


class SettlementRecord(BaseModel):
    title: str
    model: str
    brand: str
    start: date
    end: date
    deadline: date
    source_url: str
    fetched_at: datetime
    source_type: Literal["fixture"] = "fixture"
    simulated: Literal[True] = True
    proof: list[str] = Field(default_factory=lambda: ["receipt"])


class RunRequest(BaseModel):
    purchase_ids: list[str] = Field(min_length=1, max_length=100)
    mode: Literal["demo", "live"] = "demo"
    idempotency_key: str = Field(min_length=1, max_length=200)
    collaboration_mode: Literal["deterministic", "local", "band"] = "deterministic"
    fallback_of: str | None = Field(default=None, max_length=100)


class Approval(BaseModel):
    confirmed: Literal[True]


class IdentifierConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: Literal[True]
    brand: str | None = Field(default=None, max_length=100)
    model_number: str = Field(min_length=1, max_length=100, pattern=r"^[^\x00-\x1f\x7f]+$")
    upc: str | None = Field(default=None, pattern=r"^[0-9]{8,14}$")


class EntityResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    created_at: datetime
    updated_at: datetime
    demo: bool


class ProductResponse(EntityResponse):
    purchase_id: str
    product: ProductInput


class OpportunityResponse(EntityResponse):
    product_id: str
    kind: Literal["recall", "settlement"]
    title: str
    status: Literal[
        "candidate",
        "needs_review",
        "verified_match",
        "rejected",
        "expired",
        "unavailable",
        "eligible_candidate",
        "ineligible",
        "uncertain",
    ]
    source_id: str
    official_url: str
    source_observed_at: datetime
    simulated: bool
    mode: Literal["replay", "live", "fixture"]
    matching_reasons: list[str]
    purchase_model: str | None = None


class EvidenceResponse(EntityResponse):
    url: str
    publisher: str
    source_type: str
    fetched_at: datetime
    quoted_excerpt: str
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class AssessmentResponse(EntityResponse):
    outcome: Literal["eligible_candidate", "ineligible", "uncertain"]
    hard_conditions: list[Condition]
    missing_fields: list[str]
    reasons: list[str]
    performed_by: str
    evaluated_at: datetime


class DetailResponse(OpportunityResponse):
    product: ProductResponse
    evidence: list[EvidenceResponse]
    assessment: AssessmentResponse


class PacketResponse(EntityResponse):
    status: Literal["draft", "needs_evidence", "ready_for_review", "approved_local", "exported"]
    markdown: str
    contact_or_portal_url: str | None
    missing_documents: list[str]
    required_documents: list[str]
    user_declaration_required: bool
    completed_fields: dict[str, Any]
    instructions: str
    generated_at: datetime
    approved_at: datetime | None
    reviewed_at: datetime | None
    mode: Literal["replay", "live"]


class RunResponse(EntityResponse):
    run_id: str
    mode: Literal["demo", "live"]
    status: Literal["queued", "running", "completed", "partial", "failed"]
    summary: dict[str, int]
    provider_modes: dict[str, str]
    warnings: list[str]
    opportunities: list[str]
    events_url: str


class AuditResponse(EntityResponse):
    seq: int = Field(ge=1)
    stage: str
    provider: str
    outcome: str
    timestamp: datetime
    source_refs: list[str]


class ImportResponse(BaseModel):
    purchase_ids: list[str]
    product_ids: list[str]
    parse_warnings: list[str]


class ProviderHealth(BaseModel):
    name: str
    configured: bool
    enabled: bool
    healthy: bool | None = None


class HealthResponse(BaseModel):
    db: Literal["ok"]
    providers: list[ProviderHealth]
    demo_ready: bool


class CollaborationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_ids: list[str] = Field(min_length=1, max_length=1)
    idempotency_key: str = Field(min_length=1, max_length=200)
    mode: Literal["replay", "live"] = "replay"
    case_id: str | None = Field(default=None, max_length=100)


class CollaborationAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    field: Literal["model_number", "serial_prefix", "batch", "date_purchased", "region", "brand", "upc"]
    value: str = Field(min_length=1, max_length=100, pattern=r"^[^\x00-\x1f\x7f]+$")
    confirmed: Literal[True]
    idempotency_key: str = Field(min_length=1, max_length=200)
