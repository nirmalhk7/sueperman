"""Application-owned contracts, deliberately independent of vendor wire formats."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.security.source_policy import official_cpsc

Role = Literal["controller", "scout", "skeptic", "builder"]
Mode = Literal["replay", "live"]
FieldName = Literal["model_number", "serial_prefix", "batch", "date_purchased", "region", "upc", "brand"]
Status = Literal["completed", "needs_information", "rejected", "partial", "failed", "timed_out"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Start(Strict):
    product_ids: list[str] = Field(min_length=1, max_length=1)
    idempotency_key: str = Field(min_length=1, max_length=200)
    mode: Mode = "replay"


class RevisionRequest(Strict):
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")


class Answer(RevisionRequest):
    field: FieldName
    value: str = Field(min_length=1, max_length=100, pattern=r"^[^\x00-\x1f\x7f]+$")
    confirmed: Literal[True]

    @field_validator("value")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Explicit nonblank answer required")
        return value.strip()


class Approval(RevisionRequest):
    confirmed: Literal[True]


class EvidenceSnapshot(Strict):
    id: str = Field(min_length=1, max_length=100)
    publisher: str = Field(min_length=1, max_length=200)
    url: str = Field(max_length=2048)
    fetched_at: datetime
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_type: Literal["government"] = "government"
    rule_version: str = Field(max_length=100)
    excerpt: str = Field(min_length=1, max_length=16000)
    mode: Mode

    @field_validator("url")
    @classmethod
    def official_url(cls, value):
        if not official_cpsc(value):
            raise ValueError("Only supported official HTTPS recall citations are accepted")
        return value

    @field_validator("fetched_at")
    @classmethod
    def timezone_required(cls, value):
        if value.utcoffset() is None:
            raise ValueError("Source observation requires timezone")
        return value


class CaseTask(Strict):
    schema_version: Literal[1] = 1
    case_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1, max_length=100)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    sender: Role
    recipient: Literal["scout", "skeptic", "builder"]
    task_kind: Literal["source_investigation", "counterexample_review", "case_board_construction"]
    parent_task_id: str | None = Field(default=None, max_length=100)
    deduplication_key: str = Field(min_length=1, max_length=200)
    allowed_capabilities: list[Literal["read_supplied_evidence", "challenge_conditions", "build_sections"]]
    source_refs: list[str] = Field(max_length=10)
    remaining_seconds: float = Field(gt=0, le=90)
    mode: Mode


class Finding(Strict):
    code: Literal[
        "candidate", "excluded_condition", "unknown_condition", "checklist_exhausted", "no_candidate"
    ]
    condition: str | None = Field(default=None, max_length=100)
    source_ref: str | None = Field(default=None, max_length=100)


class CaseResult(Strict):
    task_id: str = Field(min_length=1, max_length=100)
    case_id: str = Field(min_length=1, max_length=100)
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    provider: Literal["local_replay", "agent37", "adal", "lyzr"]
    role: Literal["scout", "skeptic", "builder"]
    mode: Mode
    status: Status
    findings: list[Finding] = Field(max_length=30)
    missing_conditions: list[FieldName] = Field(default_factory=list, max_length=7)
    source_refs: list[str] = Field(max_length=10)
    # Private routing reference, never included in public events or exports.
    provider_reference: str | None = Field(default=None, max_length=200, pattern=r"^[\w:./-]+$")
    duration_ms: int = Field(default=0, ge=0, le=90000)
