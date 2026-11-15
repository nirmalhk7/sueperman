"""Application-owned wire contract. Provider metadata is never message authority."""

import json
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, GetJsonSchemaHandler, model_validator
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema

Role = Literal["manager", "researcher", "skeptic", "builder"]
PublicField = Literal["affected_models", "remedy_instructions", "proof_requirements", "safety_instructions"]
Reason = Literal["SOURCE_UNAVAILABLE", "DEADLINE", "INVALID_RESULT", "TRANSPORT_FAILED", "RESTART",
                 "STALE_INPUT", "BUDGET_EXHAUSTED"]
Ref = Annotated[str, Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$")]


class Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchRequested(Closed):
    product_ref: str = Field(min_length=1, max_length=200)


class ResearchReport(Closed):
    candidate_refs: list[Ref] = Field(max_length=10)
    coverage: Literal["supported_scope", "unavailable"]
    truncated: bool


class ReviewRequested(Closed):
    product_ref: str = Field(min_length=1, max_length=200)
    evidence_refs: list[Ref] = Field(min_length=1, max_length=10)


class ComparedIdentifiers(Closed):
    purchase_model: str | None = Field(max_length=100)
    source_models: list[str] = Field(max_length=10)


class RuleCondition(Closed):
    name: Literal["official_source", "brand", "product_family", "model_number", "serial_prefix", "batch",
                  "region", "upc", "date_purchased", "unsupported_source_conditions"]
    expected: str | list[str] | None
    observed: str | None = None
    status: Literal["true", "false", "unknown"]
    source_id: str


class ReviewReport(Closed):
    rule_result: Literal["verified_match", "rejected", "needs_review"]
    conditions: list[RuleCondition] = Field(max_length=20)
    compared_identifiers: ComparedIdentifiers
    challenge_code: Literal["NONE", "MODEL_MISMATCH", "CONDITION_FAILED", "MISSING_PURCHASE_FACT",
                            "MISSING_PUBLIC_FACT"]
    review_note: str = Field(max_length=1000)
    requested_fields: list[PublicField] = Field(max_length=2)


class FollowUpRequested(Closed):
    requested_fields: list[PublicField] = Field(min_length=1, max_length=2)
    evidence_refs: list[Ref] = Field(min_length=1, max_length=10)


class FollowUpReport(Closed):
    evidence_refs: list[Ref] = Field(max_length=10)
    unavailable_reason: Literal["SOURCE_UNAVAILABLE", "UNSUPPORTED_FACT"] | None


class InputDigests(Closed):
    purchase: str = Field(pattern=r"^[a-f0-9]{64}$")
    evidence: str = Field(pattern=r"^[a-f0-9]{64}$")


class BuildRequested(Closed):
    rule_result: Literal["verified_match"]
    evidence_refs: list[Ref] = Field(min_length=1, max_length=10)
    input_digests: InputDigests


class UnsignedDraft(Closed):
    markdown: str = Field(min_length=1, max_length=12000)
    status: Literal["ready_for_review"]
    approved_at: None


class CaseView(ComparedIdentifiers):
    source_ref: str = Field(min_length=1, max_length=200)


class BuildReport(Closed):
    draft: UnsignedDraft
    view: CaseView
    input_digests: InputDigests


class TaskFailed(Closed):
    reason_code: Reason
    retryable: bool


PAYLOADS = {cls.__name__: cls for cls in (
    ResearchRequested, ResearchReport, ReviewRequested, ReviewReport, FollowUpRequested,
    FollowUpReport, BuildRequested, BuildReport, TaskFailed,
)}
ROUTES = {
    "ResearchRequested": ("manager", "researcher"), "ResearchReport": ("researcher", "manager"),
    "ReviewRequested": ("manager", "skeptic"), "ReviewReport": ("skeptic", "manager"),
    "FollowUpRequested": ("manager", "researcher"), "FollowUpReport": ("researcher", "manager"),
    "BuildRequested": ("manager", "builder"), "BuildReport": ("builder", "manager"),
}


class Message(Closed):
    schema_version: Literal[1]
    message_id: UUID
    run_id: UUID
    case_id: UUID
    task_id: UUID
    correlation_id: UUID
    causation_id: UUID
    expected_case_revision: int = Field(ge=1)
    sender: Role
    recipient: Role
    type: Literal["ResearchRequested", "ResearchReport", "ReviewRequested", "ReviewReport",
                  "FollowUpRequested", "FollowUpReport", "BuildRequested", "BuildReport", "TaskFailed"]
    sent_at: AwareDatetime
    deadline_at: AwareDatetime
    source_refs: list[Ref] = Field(max_length=10)
    payload: (ResearchRequested | ResearchReport | ReviewRequested | ReviewReport | FollowUpRequested |
              FollowUpReport | BuildRequested | BuildReport | TaskFailed)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: CoreSchema, handler: GetJsonSchemaHandler) -> JsonSchemaValue:
        schema = handler.resolve_ref_schema(handler(core_schema))
        variants = schema["properties"]["payload"]["anyOf"]
        refs = {handler.resolve_ref_schema(ref)["title"]: ref for ref in variants}
        schema["oneOf"] = []
        for kind in PAYLOADS:
            route = ({"sender": {"enum": ["researcher", "skeptic", "builder"]}, "recipient": {"const": "manager"}}
                     if kind == "TaskFailed" else
                     {"sender": {"const": ROUTES[kind][0]}, "recipient": {"const": ROUTES[kind][1]}})
            schema["oneOf"].append({"properties": {"type": {"const": kind}, "payload": refs[kind], **route}})
        schema["$comment"] = ("Application also enforces 16 KiB UTF-8 payload, deadline ordering, correlation, "
                              "authenticated identities and immutable run-scoped references.")
        return schema

    @model_validator(mode="before")
    @classmethod
    def typed_payload(cls, value):
        if isinstance(value, dict) and value.get("type") in PAYLOADS:
            value = dict(value)
            payload = value.get("payload")
            raw = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
            if len(json.dumps(raw, ensure_ascii=False).encode("utf-8")) > 16384:
                raise ValueError("Payload exceeds 16 KiB")
            value["payload"] = PAYLOADS[value["type"]].model_validate(raw)
        return value

    @model_validator(mode="after")
    def validate_route(self):
        if self.type == "TaskFailed":
            if self.sender == "manager" or self.recipient != "manager":
                raise ValueError("Failure route must return to manager")
        elif ROUTES[self.type] != (self.sender, self.recipient):
            raise ValueError("Unauthorized actor route")
        if self.deadline_at <= self.sent_at:
            raise ValueError("Deadline must follow send time")
        if self.correlation_id != self.case_id:
            raise ValueError("Correlation must identify the case")
        refs = set(self.source_refs)
        for field in ("candidate_refs", "evidence_refs"):
            if not set(getattr(self.payload, field, [])).issubset(refs):
                raise ValueError("Payload contains uncited source references")
        if isinstance(self.payload, BuildReport) and self.payload.view.source_ref not in refs:
            raise ValueError("Build view contains uncited source")
        return self


def validate_delivery(message: Message, sender: str, recipient: str, registry: dict[str, str]) -> None:
    if set(registry) != {"manager", "researcher", "skeptic", "builder"} or len(set(registry.values())) != 4:
        raise ValueError("Four distinct authenticated identities required")
    if registry.get(message.sender) != sender or registry.get(message.recipient) != recipient:
        raise ValueError("Authenticated identity does not match actor route")


def validate_sources(message: Message, snapshots: dict, expected_digests: dict[str, str]) -> None:
    for ref in message.source_refs:
        snapshot = snapshots.get(ref)
        expected = expected_digests.get(ref)
        if (not snapshot or not expected or len(expected) != 64
                or any(c not in "0123456789abcdef" for c in expected)
                or snapshot.get("run_id") != str(message.run_id) or snapshot.get("digest") != expected):
            raise ValueError("Reference does not resolve to immutable run snapshot")
