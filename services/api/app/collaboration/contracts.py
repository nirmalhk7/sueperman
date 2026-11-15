"""Application contracts, never vendor payloads. No executable free-form fields."""

from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.security.source_policy import official_cpsc

Role = Literal["controller", "scout", "skeptic", "builder"]
Mode = Literal["replay", "live"]
FieldName = Literal[
    "model_number",
    "serial_prefix",
    "batch",
    "date_purchased",
    "region",
    "brand",
    "upc",
    "product_family",
    "official_source",
    "unsupported_source_conditions",
]
Status = Literal["completed", "needs_information", "rejected", "partial", "failed", "timed_out"]
Lifecycle = Literal[
    "queued",
    "investigating",
    "challenging",
    "building",
    "needs_information",
    "ready_for_review",
    "rejected",
    "partial",
    "failed",
]
Identifier = str


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseTask(Strict):
    schema_version: Literal[1] = 1
    case_id: str = Field(min_length=1, max_length=100)
    task_id: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=1)
    sender: Role
    recipient: Literal["scout", "skeptic", "builder"]
    kind: Literal["source_investigation", "counterexample_review", "case_board_construction"]
    parent_task_id: str | None = Field(default=None, max_length=100)
    deduplication_key: str = Field(min_length=1, max_length=200)
    allowed_capabilities: list[
        Literal["supported_source_read", "review_supplied_evidence", "build_sections"]
    ] = Field(default_factory=list, max_length=3)
    source_refs: list[str] = Field(default_factory=list, max_length=10)
    remaining_ms: int = Field(ge=1, le=90000)
    mode: Mode

    @model_validator(mode="after")
    def addressed_role(self):
        routes = {
            "source_investigation": ("controller", "scout"),
            "counterexample_review": ("scout", "skeptic"),
            "case_board_construction": ("skeptic", "builder"),
        }
        if (self.sender, self.recipient) != routes[self.kind]:
            raise ValueError("Unregistered task route")
        capability = {
            "scout": "supported_source_read",
            "skeptic": "review_supplied_evidence",
            "builder": "build_sections",
        }[self.recipient]
        if not set(self.allowed_capabilities) <= {capability}:
            raise ValueError("Capability outside registered role")
        return self


class Finding(Strict):
    code: Literal["candidate", "condition_passed", "condition_failed", "condition_unknown", "no_candidate"]
    condition: FieldName | None = None
    source_ref: str = Field(min_length=1, max_length=200)


class CaseResult(Strict):
    schema_version: Literal[1] = 1
    task_id: str = Field(min_length=1, max_length=100)
    case_id: str = Field(min_length=1, max_length=100)
    revision: int = Field(ge=1)
    provider: Literal["offline_rules", "agent37", "adal", "lyzr"]
    mode: Mode
    status: Status
    findings: list[Finding] = Field(default_factory=list, max_length=30)
    missing_conditions: list[FieldName] = Field(default_factory=list, max_length=10)
    source_refs: list[str] = Field(default_factory=list, max_length=10)
    provider_ref: str | None = Field(default=None, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    duration_ms: int = Field(default=0, ge=0, le=90000)


class EvidenceSnapshot(Strict):
    source_id: str = Field(min_length=1, max_length=200)
    publisher: str = Field(min_length=1, max_length=200)
    url: str = Field(max_length=2000)
    fetched_at: datetime
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_type: Literal["government"]
    rule_version: str = Field(min_length=1, max_length=100)
    excerpt: str = Field(min_length=1, max_length=20000)
    mode: Mode

    @field_validator("url")
    @classmethod
    def trusted_source(cls, value):
        parts = urlsplit(value)
        if (
            not official_cpsc(value)
            or parts.username
            or parts.password
            or parts.port not in {None, 443}
            or parts.query
            or parts.fragment
        ):
            raise ValueError("Source URL not allowed")
        return value

    @field_validator("fetched_at")
    @classmethod
    def utc_time(cls, value):
        if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
            raise ValueError("Evidence observation must be UTC")
        return value


class CaseRevision(Strict):
    product_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence_hashes: list[str] = Field(max_length=10)
    rule_version: str = Field(min_length=1, max_length=100)
    skill_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class DraftApproval(Strict):
    packet_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision_fingerprint: str = Field(pattern=r"^[a-f0-9]{64}$")


def validate_result(task: CaseTask, result: CaseResult, available: set[str]) -> None:
    if (result.case_id, result.task_id, result.revision, result.mode) != (
        task.case_id,
        task.task_id,
        task.revision,
        task.mode,
    ):
        raise ValueError("Stale or wrong-case result")
    expected_provider = {"scout": "agent37", "skeptic": "adal", "builder": "lyzr"}[task.recipient]
    if result.provider != ("offline_rules" if task.mode == "replay" else expected_provider):
        raise ValueError("Wrong provider identity")
    refs = set(result.source_refs) | {finding.source_ref for finding in result.findings}
    if not refs <= available or (task.source_refs and not refs <= set(task.source_refs)):
        raise ValueError("Unknown evidence citation")
    if result.status == "completed" and result.findings and not result.source_refs:
        raise ValueError("Completed findings require citations")
