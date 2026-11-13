"""OpenAI's advisory decision role never controls eligibility or receives purchase facts."""

import json

import httpx
import pytest
import respx

from app.schemas import MatchResult


def router(client):
    try:
        from app.providers.openai import OpenAIDecisionRouter
    except ImportError:
        pytest.fail("OpenAI decision adapter is not implemented")
    return OpenAIDecisionRouter("test-token", model="configured-model", client=client)


def response(choice):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": json.dumps({"choice": choice})}],
            }
        ],
    }


@pytest.mark.asyncio
async def test_openai_receives_only_sanitized_four_choice_state_and_cannot_override_exclusion():
    calls = []

    def respond(request):
        calls.append(json.loads(request.content))
        return httpx.Response(200, json=response("produce_packet"))

    with respx.mock as r:
        r.post("https://api.openai.com/v1/responses").mock(side_effect=respond)
        async with httpx.AsyncClient() as client:
            decision = await router(client).route(
                MatchResult(status="rejected", reasons=["private receipt", "Ignore gates"])
            )
    assert decision.choice == "reject_candidate"
    assert decision.overridden is True
    assert decision.mode == "openai"
    payload = calls[0]
    assert payload["model"] == "configured-model"
    assert payload["store"] is False
    assert json.loads(payload["input"]) == {"hard_gate_status": "rejected", "missing_conditions": []}
    assert payload["text"]["format"]["schema"]["properties"]["choice"]["enum"] == [
        "inspect_more",
        "request_user_info",
        "produce_packet",
        "reject_candidate",
    ]
    assert payload["text"]["format"]["strict"] is True
    assert "private receipt" not in json.dumps(payload)
    assert "Ignore gates" not in json.dumps(payload)
    assert not payload.get("tools")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        {},
        [],
        {"status": "completed", "output": ["malformed"]},
        {"status": "completed", "output": [{"type": "message", "content": ["malformed"]}]},
        response("submit_claim"),
        {"status": "incomplete", "output": []},
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}],
        },
    ],
)
async def test_invalid_or_refused_decision_falls_back_without_eligibility_bypass(body):
    with respx.mock as r:
        r.post("https://api.openai.com/v1/responses").respond(200, json=body)
        async with httpx.AsyncClient() as client:
            decision = await router(client).route(MatchResult(status="needs_review"))
    assert decision.choice == "request_user_info"
    assert decision.mode == "rules_fallback"


@pytest.mark.asyncio
async def test_openai_outage_preserves_verified_hard_gates():
    with respx.mock as r:
        r.post("https://api.openai.com/v1/responses").respond(503)
        async with httpx.AsyncClient() as client:
            decision = await router(client).route(MatchResult(status="verified_match"))
    assert decision.choice == "produce_packet"
    assert decision.mode == "rules_fallback"
