"""Actual pinned SDK at a controlled HTTP boundary; none of these are live proof."""

import importlib
import json
from datetime import timedelta
from uuid import UUID

import httpx
import pytest
from test_local_core import fixture_data, inputs

from app.diwali.core import CaseState, Start, reduce_case
from app.diwali.message_schema import Message


def bridge():
    try:
        return importlib.import_module("app.diwali.band_bridge")
    except ModuleNotFoundError:
        pytest.fail("Pinned BAND custom adapter is not implemented")


def case():
    product, recall = fixture_data()
    context = inputs(product[0], recall)
    _state, commands = reduce_case(CaseState(context), Start())
    return context, commands[0].message


def registry():
    return {role: str(UUID(int=20 + i)) for i, role in enumerate(["manager", "researcher", "skeptic", "builder"])}


def platform(message, *, sender=None, room="private-test-room"):
    from band.core.types import PlatformMessage
    return PlatformMessage(id=str(UUID(int=80)), room_id=room,
        content=f"@[[{registry()[message.recipient]}]] " + message.model_dump_json(),
        sender_id=sender or registry()[message.sender], sender_type="Agent", sender_name="Synthetic agent",
        message_type="text", metadata={}, created_at=message.sent_at)


@pytest.mark.asyncio
async def test_sdk_sender_addresses_exact_recipient_without_post_retry():
    module = bridge()
    from band.client.rest import AsyncRestClient
    from band_rest.core.api_error import ApiError
    _context, wire = case()
    requests = []
    def receive(request):
        requests.append(request)
        return httpx.Response(503, json={"error": {"code": "service_unavailable",
            "message": "injected temporary failure", "request_id": "offline-request"}})
    async with httpx.AsyncClient(transport=httpx.MockTransport(receive)) as http:
        rest = AsyncRestClient(api_key="offline-test-key", base_url="https://band.example.test", httpx_client=http,
                               follow_redirects=False)
        with pytest.raises(ApiError):
            await module.send_wire(rest, "private-test-room", wire, registry(), timeout=1)
    assert len(requests) == 1
    assert requests[0].url.path == "/api/v1/agent/chats/private-test-room/messages"
    body = json.loads(requests[0].content)
    assert body["message"]["mentions"] == [{"id": registry()["researcher"]}]
    assert Message.model_validate_json(body["message"]["content"]) == wire
    assert requests[0].headers["X-API-Key"] == "offline-test-key"


@pytest.mark.asyncio
async def test_sdk_adapter_runs_same_research_handler_and_replies_to_manager():
    module = bridge()
    from band.testing import FakeAgentTools
    context, request = case()
    sent = []
    async def send(message):
        sent.append(message)
        return "synthetic-platform-reference"
    adapter = module.CaseBandAdapter("researcher", registry(), "private-test-room", lambda _: context,
        send, clock=lambda: context.started_at)
    tools = FakeAgentTools()
    await adapter.on_message(platform(request), tools, [], None, None,
                             is_session_bootstrap=True, room_id="private-test-room")
    assert len(sent) == 1
    assert sent[0].type == "ResearchReport"
    assert sent[0].sender == "researcher" and sent[0].recipient == "manager"
    assert sent[0].payload.candidate_refs == list(context.sources)
    assert tools.turn.complete  # No model turn or fabricated SDK fallback message.


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["sender", "room", "expired"])
async def test_unauthenticated_or_expired_platform_message_does_not_dispatch(fault):
    module = bridge()
    from band.testing import FakeAgentTools
    context, request = case()
    sent = []
    async def send(message):
        sent.append(message)
    adapter = module.CaseBandAdapter("researcher", registry(), "private-test-room", lambda _: context,
        send, clock=lambda: context.started_at + timedelta(seconds=11 if fault == "expired" else 0))
    msg = platform(request, sender=registry()["builder"] if fault == "sender" else None,
                   room="other-room" if fault == "room" else "private-test-room")
    tools = FakeAgentTools()
    await adapter.on_message(msg, tools, [], None, None, is_session_bootstrap=False, room_id=msg.room_id)
    assert sent == []
    assert adapter.rejections
    assert tools.turn.complete


@pytest.mark.asyncio
async def test_redelivery_does_not_send_result_twice():
    module = bridge()
    from band.testing import FakeAgentTools
    context, request = case()
    sent = []
    async def send(message):
        sent.append(message)
    adapter = module.CaseBandAdapter("researcher", registry(), "private-test-room", lambda _: context,
        send, clock=lambda: context.started_at)
    for _ in range(2):
        await adapter.on_message(platform(request), FakeAgentTools(), [], None, None,
                                 is_session_bootstrap=False, room_id="private-test-room")
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_wrong_product_reference_cannot_run_authenticated_research():
    module = bridge()
    from band.testing import FakeAgentTools
    context, request = case()
    request = Message.model_validate(request.model_dump(mode="json") | {
        "payload": {"product_ref": "another-product"}})
    sent = []
    async def send(message):
        sent.append(message)
    adapter = module.CaseBandAdapter("researcher", registry(), "private-test-room", lambda _: context,
        send, clock=lambda: context.started_at)
    await adapter.on_message(platform(request), FakeAgentTools(), [], None, None,
                             is_session_bootstrap=False, room_id="private-test-room")
    assert sent == []
    assert adapter.rejections == ["INVALID_PLATFORM_MESSAGE"]
