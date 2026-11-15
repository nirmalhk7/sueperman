"""Catch executable payloads, untrusted sources and fabricated citations at ingress."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError


def contracts():
    try:
        from app.collaboration import contracts

        return contracts
    except ImportError:
        pytest.fail("V2 strict collaboration contracts missing")


def test_task_rejects_commands_unknown_roles_and_unbounded_deadlines():
    c = contracts()
    task = {
        "case_id": "case",
        "task_id": "task",
        "revision": 1,
        "sender": "controller",
        "recipient": "scout",
        "kind": "source_investigation",
        "deduplication_key": "once",
        "remaining_ms": 90000,
        "mode": "replay",
    }
    assert c.CaseTask(**task).allowed_capabilities == []
    for extra in (
        {"command": "rm -rf /"},
        {"sender": "intruder"},
        {"remaining_ms": 90001},
        {"allowed_capabilities": ["shell"]},
        {"schema_version": 2},
    ):
        with pytest.raises(ValidationError):
            c.CaseTask(**(task | extra))


@pytest.mark.parametrize(
    "url",
    [
        "http://www.cpsc.gov/Recalls/x",
        "https://www.cpsc.gov.evil.test/Recalls/x",
        "https://user:pass@www.cpsc.gov/Recalls/x",
        "https://127.0.0.1/x",
        "https://www.cpsc.gov:444/Recalls/x",
    ],
)
def test_snapshot_rejects_untrusted_urls(url):
    c = contracts()
    with pytest.raises(ValidationError):
        c.EvidenceSnapshot(
            source_id="s",
            publisher="CPSC",
            url=url,
            fetched_at=datetime.now(UTC),
            content_sha256="a" * 64,
            source_type="government",
            rule_version="26-792-v1",
            excerpt="public",
            mode="replay",
        )


def test_result_rejects_foreign_citations_and_unsupported_claims():
    c = contracts()
    task = c.CaseTask(
        case_id="case",
        task_id="t",
        revision=2,
        sender="scout",
        recipient="skeptic",
        kind="counterexample_review",
        deduplication_key="k",
        remaining_ms=1000,
        source_refs=["source"],
        mode="replay",
    )
    base = {
        "task_id": "t",
        "case_id": "case",
        "revision": 2,
        "provider": "offline_rules",
        "mode": "replay",
        "status": "completed",
        "source_refs": ["source"],
        "findings": [],
    }
    result = c.CaseResult(**base)
    c.validate_result(task, result, {"source"})
    for delta in ({"revision": 1}, {"case_id": "other"}, {"source_refs": ["fake"]}, {"mode": "live"}):
        with pytest.raises(ValueError):
            c.validate_result(task, c.CaseResult(**(base | delta)), {"source"})
    for delta in (
        {"payment_guaranteed": True},
        {"findings": [{"code": "eligible", "source_ref": "source"}]},
        {"missing_conditions": ["social_security_number"]},
        {"provider_ref": "Bearer secret"},
    ):
        with pytest.raises(ValidationError):
            c.CaseResult(**(base | delta))


def test_role_cannot_request_other_roles_capabilities():
    c = contracts()
    with pytest.raises(ValidationError):
        c.CaseTask(
            case_id="case",
            task_id="task",
            revision=1,
            sender="skeptic",
            recipient="builder",
            kind="case_board_construction",
            deduplication_key="k",
            remaining_ms=1000,
            allowed_capabilities=["supported_source_read"],
            mode="replay",
        )
