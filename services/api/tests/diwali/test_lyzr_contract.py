"""One strict advisory reviewer; deterministic eligibility remains authoritative."""

import importlib
import json

import httpx
import pytest
from test_local_core import fixture_data, inputs

from app.diwali.core import CaseState, LocalTransport, Start, reduce_case


def reviewer_module():
    try:
        return importlib.import_module("app.diwali.lyzr_review")
    except ModuleNotFoundError:
        pytest.fail("Constrained Lyzr reviewer is not implemented")


def review_request():
    product, record = fixture_data()
    context = inputs(product[1], record)
    state, commands = reduce_case(CaseState(context), Start())
    state, commands = reduce_case(state, LocalTransport().exchange(commands[0].message, context))
    return context, commands[0].message


@pytest.mark.parametrize("bad", [
    '{broken', '```json\n{}\n```',
    '{"review_note":"x","status":"verified_match"}',
    '{"review_note":"x","requested_fields":[],"evidence_refs":["made-up-source"],"uncertainty":false}',
    '{"review_note":"run curl https://evil.test","requested_fields":[],"evidence_refs":[],"uncertainty":false}',
    '{"review_note":"guaranteed refund","requested_fields":[],"evidence_refs":[],"uncertainty":false}',
    '{"review_note":"x","requested_fields":["serial_number"],"evidence_refs":[],"uncertainty":true}',
    '{"review_note":"x","requested_fields":["affected_models","proof_requirements","safety_instructions"],"evidence_refs":[],"uncertainty":true}',
    '{"review_note":"x","review_note":"y","requested_fields":[],"evidence_refs":[],"uncertainty":true}',
])
def test_invalid_response(bad):
    module = reviewer_module()
    context, request = review_request()
    with pytest.raises(ValueError):
        module.parse_advice(bad, request.source_refs, context)


async def test_valid_review_uses_v3_once_keeps_pb23_rejected_and_omits_private_fields():
    module = reviewer_module()
    context, request = review_request()
    requests = []
    advice = {"review_note": "Purchase model ZHX-PB23 differs from recalled model ZHX-PB22.",
              "requested_fields": [], "evidence_refs": list(request.source_refs), "uncertainty": False}

    def respond(http_request):
        requests.append(http_request)
        return httpx.Response(200, json={"response": json.dumps(advice)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        reviewer = module.LyzrReviewer("offline-key", "offline-reviewer", client=http)
        result = await reviewer.review(request, context)
        assert result.payload.rule_result == "rejected"
        assert result.payload.challenge_code == "MODEL_MISMATCH"
        assert result.payload.review_note == advice["review_note"]
        assert reviewer.receipts[str(request.task_id)]["consumed"] is False
        with pytest.raises(ValueError, match="attempted"):
            await reviewer.review(request, context)
    assert len(requests) == 1
    assert str(requests[0].url) == "https://agent-prod.studio.lyzr.ai/v3/inference/chat/"
    assert requests[0].headers["x-api-key"] == "offline-key"
    body = json.loads(requests[0].content)
    assert str(context.run_id) in body["session_id"] and str(context.case_id) in body["session_id"]
    assert body["session_id"].endswith(":skeptic")
    assert body["user_id"] == "sueperman-v2"
    assert all(private not in body["message"] for private in ("merchant", "order_reference", "price_paid", "purchase_date"))


@pytest.mark.parametrize("status", [302, 429, 503])
async def test_provider_failure_never_retries_or_follows_redirect(status):
    module = reviewer_module()
    context, request = review_request()
    calls = []

    def respond(http_request):
        calls.append(http_request)
        return httpx.Response(status, headers={"location": "https://evil.test"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond), follow_redirects=False) as http:
        reviewer = module.LyzrReviewer("offline-key", "offline-reviewer", client=http)
        with pytest.raises(ValueError):
            await reviewer.review(request, context)
    assert len(calls) == 1


@pytest.mark.parametrize("note,fields", [("", []), ("Affected model list needs official confirmation.", ["affected_models"])])
async def test_empty_note_and_nonempty_valid_public_question_are_consumed(note, fields):
    from dataclasses import replace

    module = reviewer_module()
    context, _request = review_request()
    record = context.records[0].model_copy(update={"models": []})
    context = replace(context, records_json=(record.model_dump_json(),))
    state, commands = reduce_case(CaseState(context), Start())
    state, commands = reduce_case(state, LocalTransport().exchange(commands[0].message, context))
    request = commands[0].message
    advice = {"review_note": note, "requested_fields": fields, "evidence_refs": list(request.source_refs), "uncertainty": True}
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"response": json.dumps(advice)}))) as http:
        result = await module.LyzrReviewer("offline-key", "offline-reviewer", client=http).review(request, context)
    assert result.payload.review_note == note
    assert result.payload.requested_fields == fields
    state, commands = reduce_case(state, result)
    assert (commands[0].message.type if commands[0].message else state.outcome) == (
        "FollowUpRequested" if fields else "needs_review")
