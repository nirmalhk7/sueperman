"""Closed-wire safety: wrong routes, shape and context must fail before dispatch."""

import importlib
from copy import deepcopy

import pytest
from pydantic import ValidationError


def contract():
    try:
        return importlib.import_module("app.diwali.message_schema")
    except ModuleNotFoundError:
        pytest.fail("V2.1 closed message contract is not implemented")


def envelope():
    return {
        "schema_version": 1,
        "message_id": "11111111-1111-4111-8111-111111111111",
        "run_id": "22222222-2222-4222-8222-222222222222",
        "case_id": "33333333-3333-4333-8333-333333333333",
        "task_id": "44444444-4444-4444-8444-444444444444",
        "correlation_id": "33333333-3333-4333-8333-333333333333",
        "causation_id": "55555555-5555-4555-8555-555555555555",
        "expected_case_revision": 1,
        "sender": "manager", "recipient": "researcher", "type": "ResearchRequested",
        "sent_at": "2026-11-15T00:00:00Z", "deadline_at": "2026-11-15T00:00:10Z",
        "source_refs": [], "payload": {"product_ref": "product-1"},
    }


def test_closed_message_accepts_research_request():
    message = contract().Message.model_validate(envelope())
    assert message.payload.product_ref == "product-1"
    assert message.sender == "manager"


@pytest.mark.parametrize("change", [
    {"sender": "scout"}, {"recipient": "builder"}, {"type": "ChallengeRaised"},
    {"mode": "live"}, {"expected_case_revision": 0},
    {"sent_at": "2026-11-15T00:00:00"}, {"deadline_at": "2026-11-14T00:00:00Z"},
    {"payload": {"product_ref": "product-1", "eligible": True}},
    {"message_id": "not-a-uuid"},
    {"source_refs": ["x" * 201]}, {"source_refs": ["cpsc:26-792\nforged"]},
])
def test_invalid_envelope_rejected(change):
    with pytest.raises(ValidationError):
        contract().Message.model_validate(envelope() | change)


def test_payload_utf8_limit():
    data = envelope()
    data["payload"] = {"product_ref": "界" * 6000}
    with pytest.raises(ValidationError):
        contract().Message.model_validate(data)


def test_authenticated_route_checked_before_handler():
    module = contract()
    message = module.Message.model_validate(envelope())
    registry = {"manager": "identity-m", "researcher": "identity-r",
                "skeptic": "identity-s", "builder": "identity-b"}
    module.validate_delivery(message, "identity-m", "identity-r", registry)
    with pytest.raises(ValueError, match="identity"):
        module.validate_delivery(message, "identity-s", "identity-r", registry)
    incomplete = registry | {"unknown": registry["builder"]}
    del incomplete["builder"]
    with pytest.raises(ValueError):
        module.validate_delivery(message, "identity-m", "identity-r", incomplete)


def test_references_bound_to_immutable_run_snapshot():
    module = contract()
    data = envelope() | {"sender": "researcher", "recipient": "manager", "type": "ResearchReport",
                         "source_refs": ["cpsc:26-792:snapshot-1"],
                         "payload": {"candidate_refs": ["cpsc:26-792:snapshot-1"],
                                     "coverage": "supported_scope", "truncated": False}}
    message = module.Message.model_validate(data)
    snapshots = {"cpsc:26-792:snapshot-1": {"run_id": str(message.run_id), "digest": "a" * 64}}
    module.validate_sources(message, snapshots, {"cpsc:26-792:snapshot-1": "a" * 64})
    bad = deepcopy(snapshots)
    bad["cpsc:26-792:snapshot-1"]["run_id"] = "another-run"
    with pytest.raises(ValueError, match="snapshot"):
        module.validate_sources(message, bad, {"cpsc:26-792:snapshot-1": "a" * 64})
    with pytest.raises(ValueError, match="snapshot"):
        module.validate_sources(message, snapshots, {"cpsc:26-792:snapshot-1": "b" * 64})
    with pytest.raises(ValueError, match="snapshot"):
        module.validate_sources(message, {"cpsc:26-792:snapshot-1": {"run_id": str(message.run_id)}}, {})


def test_report_cannot_add_uncited_candidate():
    data = envelope() | {"sender": "researcher", "recipient": "manager", "type": "ResearchReport",
                         "payload": {"candidate_refs": ["invented"], "coverage": "supported_scope",
                                     "truncated": False}}
    with pytest.raises(ValidationError):
        contract().Message.model_validate(data)


@pytest.mark.parametrize("kind,sender,recipient,payload", [
    ("ReviewRequested", "manager", "skeptic", {"product_ref": "p1", "evidence_refs": ["s1"]}),
    ("ReviewReport", "skeptic", "manager", {"rule_result": "rejected", "conditions": [],
        "compared_identifiers": {"purchase_model": "ZHX-PB23", "source_models": ["ZHX-PB22"]},
        "challenge_code": "MODEL_MISMATCH", "review_note": "", "requested_fields": []}),
    ("FollowUpRequested", "manager", "researcher", {"requested_fields": ["affected_models"],
                                                       "evidence_refs": ["s1"]}),
    ("FollowUpReport", "researcher", "manager", {"evidence_refs": [],
                                                 "unavailable_reason": "SOURCE_UNAVAILABLE"}),
    ("BuildRequested", "manager", "builder", {"rule_result": "verified_match", "evidence_refs": ["s1"],
        "input_digests": {"purchase": "a" * 64, "evidence": "b" * 64}}),
    ("BuildReport", "builder", "manager", {"draft": {"markdown": "Source-cited unsigned draft",
        "status": "ready_for_review", "approved_at": None}, "view": {"purchase_model": "ZHX-PB22",
        "source_models": ["ZHX-PB22"], "source_ref": "s1"},
        "input_digests": {"purchase": "a" * 64, "evidence": "b" * 64}}),
    ("TaskFailed", "researcher", "manager", {"reason_code": "SOURCE_UNAVAILABLE", "retryable": False}),
])
def test_closed_payloads(kind, sender, recipient, payload):
    data = envelope() | {"type": kind, "sender": sender, "recipient": recipient,
                         "source_refs": ["s1"], "payload": payload}
    message = contract().Message.model_validate(data)
    assert message.type == kind
    data["payload"] = payload | {"shell": "rm -rf /"}
    with pytest.raises(ValidationError):
        contract().Message.model_validate(data)


def test_build_request_cannot_accept_unverified_assessment():
    data = envelope() | {"type": "BuildRequested", "recipient": "builder", "source_refs": ["s1"],
        "payload": {"rule_result": "needs_review", "evidence_refs": ["s1"],
                    "input_digests": {"purchase": "a" * 64, "evidence": "b" * 64}}}
    with pytest.raises(ValidationError):
        contract().Message.model_validate(data)


def test_exported_json_schema_enforces_type_payload_and_route():
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import ValidationError as SchemaValidationError
    validator = Draft202012Validator(contract().Message.model_json_schema())
    validator.validate(envelope())
    wrong_payload = envelope() | {"payload": {"reason_code": "SOURCE_UNAVAILABLE", "retryable": False}}
    with pytest.raises(SchemaValidationError):
        validator.validate(wrong_payload)
    with pytest.raises(SchemaValidationError):
        validator.validate(envelope() | {"recipient": "builder"})
