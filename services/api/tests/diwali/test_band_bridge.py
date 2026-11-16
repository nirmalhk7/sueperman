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


@pytest.mark.asyncio
async def test_sdk_websocket_failure_is_single_attempt_and_success_cannot_reconnect(monkeypatch):
    import asyncio
    import logging

    from band.client.streaming.client import WebSocketClient
    from band.client.streaming.errors import WebSocketUpgradeError

    module = bridge()
    client_type = getattr(module, "SingleAttemptWebSocket", WebSocketClient)
    attempts = []

    class OfflineSocket:
        auto_reconnect = False
        logger = logging.getLogger("offline-socket-test")
        redact_diagnostic = staticmethod(str)
        channel_socket_url = "wss://offline.example.test"

        async def __aenter__(self):
            attempts.append(1)
            raise WebSocketUpgradeError(status_code=503, message="offline service outage")

        async def __aexit__(self, *args):
            pass

    socket = client_type("wss://offline.example.test", "offline-test-key")
    monkeypatch.setattr(socket, "_build_phx_client", OfflineSocket)
    try:
        async with asyncio.timeout(0.05):
            with pytest.raises(WebSocketUpgradeError):
                await socket.__aenter__()
    except TimeoutError:
        pytest.fail("BAND SDK retried a failed socket instead of returning its first failure")
    assert len(attempts) == 1
    await socket.__aexit__(None, None, None)

    class ConnectedSocket(OfflineSocket):
        async def __aenter__(self):
            return self

    socket = client_type("wss://offline.example.test", "offline-test-key")
    monkeypatch.setattr(socket, "_build_phx_client", ConnectedSocket)
    await socket.__aenter__()
    assert socket.client.auto_reconnect is False
    await socket.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_runtime_uses_authenticated_receipt_and_refuses_repeat_dispatch(monkeypatch):
    from band.testing import FakeAgentTools

    module = bridge()
    context, request = case()
    if not hasattr(module, "BandTransport"):
        pytest.fail("BAND transport cannot exchange a persisted coordinator task")
    credentials = {"room_id": "private-test-room", "actors": {
        role: {"agent_id": identifier, "api_key": f"offline-key-{role}"} for role, identifier in registry().items()}}
    transport = module.BandTransport(credentials)
    sent = []

    async def platform_send(rest, room_id, wire, identities, *, timeout):
        sent.append(wire.type)
        recipient = transport.adapters[wire.recipient]
        await recipient.on_message(platform(wire), FakeAgentTools(), [], None, None,
            is_session_bootstrap=False, room_id=room_id)
        return f"synthetic-platform-{wire.type}"

    monkeypatch.setattr(module, "send_wire", platform_send)
    # Reuse the real adapters without starting authenticated SDK connections.
    transport.clock = lambda: context.started_at
    transport.prepare()
    for adapter in transport.adapters.values():
        adapter.clock = transport.clock
    try:
        response = await transport.exchange(request, context)
        assert response.type == "ResearchReport"
        assert transport.last_receipt["request_id"] == "synthetic-platform-ResearchRequested"
        assert transport.last_receipt["result_id"] == str(UUID(int=80))
        assert transport.last_receipt["authenticated_sender"] == registry()["researcher"]
        assert sent == ["ResearchRequested", "ResearchReport"]
        with pytest.raises(ValueError, match="already dispatched"):
            await transport.exchange(request, context)
        assert len(sent) == 2
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_sdk_metadata_rate_limit_cannot_retry_or_redirect(monkeypatch):
    from band.runtime.platform_runtime import PlatformRuntime

    module = bridge()
    if not hasattr(module, "BandTransport"):
        pytest.fail("BAND operator runtime is missing")
    requests = []
    original = httpx.AsyncClient

    def reject(request):
        requests.append(request)
        return httpx.Response(429, json={"error": {"code": "rate_limited", "message": "offline limit"}})

    def client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(reject)
        return original(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    transport = module.BandTransport({"room_id": "private-test-room", "actors": {
        role: {"agent_id": identifier, "api_key": f"offline-{role}"} for role, identifier in registry().items()}})
    transport.prepare()
    # Real PlatformRuntime.initialize includes a metadata-specific 429 retry loop
    # in addition to generated REST retries. Both must see the first failure.
    runtime = transport.agents[0]._runtime
    assert isinstance(runtime, PlatformRuntime)
    try:
        with pytest.raises(httpx.HTTPStatusError):
            await runtime.initialize()
        assert len(requests) == 1
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_runtime_allows_first_delivery_but_sdk_rejects_second_attempt():
    from band_sdk_core import RetryTracker

    module = bridge()
    transport = module.BandTransport({"room_id": "private-test-room", "actors": {
        role: {"agent_id": identifier, "api_key": f"offline-{role}"} for role, identifier in registry().items()}})
    transport.prepare()
    try:
        # Pinned SDK calls this "max_message_retries" but documents total attempts.
        # Zero prevented the very first real delivery; one permits it exactly once.
        configured = transport.agents[0]._runtime.session_config.max_message_retries
        tracker = RetryTracker(max_retries=configured)
        assert tracker.record_attempt("offline-task") == (1, False)
        assert tracker.record_attempt("offline-task") == (2, True)
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_skeptic_consumes_injected_reviewer_note_with_correlated_receipt(monkeypatch):
    from band.testing import FakeAgentTools
    from test_lyzr_contract import review_request

    from app.diwali.core import reply, review_payload

    module = bridge()
    context, request = review_request()

    class OfflineReviewer:
        def __init__(self):
            self.receipts = {}

        async def review(self, wire, frozen):
            self.receipts[str(wire.task_id)] = {"response_sha256": "a" * 64, "mode": "fixture", "consumed": False}
            report = review_payload(frozen, wire.source_refs).model_copy(update={"review_note": "Models differ; inspect evidence."})
            return reply(wire, "ReviewReport", report.model_dump(mode="json"), list(wire.source_refs))

    credentials = {"room_id": "private-test-room", "actors": {
        role: {"agent_id": identifier, "api_key": f"offline-key-{role}"} for role, identifier in registry().items()}}
    try:
        transport = module.BandTransport(credentials, reviewer=OfflineReviewer())
    except TypeError:
        transport = module.BandTransport(credentials)
    transport.clock = lambda: context.started_at

    async def platform_send(rest, room_id, wire, identities, *, timeout):
        await transport.adapters[wire.recipient].on_message(platform(wire), FakeAgentTools(), [], None, None,
            is_session_bootstrap=False, room_id=room_id)
        return f"synthetic-platform-{wire.type}"

    monkeypatch.setattr(module, "send_wire", platform_send)
    transport.prepare()
    try:
        response = await transport.exchange(request, context)
        assert response.payload.rule_result == "rejected"
        assert response.payload.review_note == "Models differ; inspect evidence."
        assert transport.last_receipt["reviewer"]["response_sha256"] == "a" * 64
    finally:
        await transport.close()


@pytest.mark.asyncio
async def test_enabled_reviewer_failure_returns_sanitized_task_failure_without_retry():
    from band.testing import FakeAgentTools
    from test_lyzr_contract import review_request

    module = bridge()
    context, request = review_request()
    sent = []

    class FailingReviewer:
        calls = 0

        async def review(self, wire, frozen):
            self.calls += 1
            raise ValueError("private-provider-error-do-not-publish")

    async def send(wire):
        sent.append(wire)

    reviewer = FailingReviewer()
    adapter = module.CaseBandAdapter("skeptic", registry(), "private-test-room", lambda _: context,
        send, clock=lambda: context.started_at, reviewer=reviewer)
    await adapter.on_message(platform(request), FakeAgentTools(), [], None, None,
        is_session_bootstrap=False, room_id="private-test-room")
    assert reviewer.calls == 1
    assert len(sent) == 1
    assert sent[0].type == "TaskFailed"
    assert sent[0].payload.reason_code == "INVALID_RESULT"
    assert "private-provider-error" not in sent[0].model_dump_json()


@pytest.mark.asyncio
async def test_known_case_does_not_authorize_unregistered_paid_review_task(monkeypatch):
    from uuid import uuid4

    from band.testing import FakeAgentTools
    from test_lyzr_contract import review_request

    from app.diwali.core import reply, review_payload

    module = bridge()
    context, request = review_request()
    calls = []
    sent = []

    class PaidBoundary:
        receipts = None

        async def review(self, wire, frozen):
            calls.append(wire.task_id)
            return reply(wire, "ReviewReport", review_payload(frozen, wire.source_refs).model_dump(mode="json"), list(wire.source_refs))

    async def send(*args, **kwargs):
        sent.append(1)
        return "offline-platform-id"

    monkeypatch.setattr(module, "send_wire", send)
    transport = module.BandTransport({"room_id": "private-test-room", "actors": {
        role: {"agent_id": identifier, "api_key": f"offline-key-{role}"} for role, identifier in registry().items()}},
        reviewer=PaidBoundary())
    transport.clock = lambda: context.started_at
    transport.prepare()
    transport.contexts[context.case_id] = context  # Known earlier case, no active task.
    forged = Message.model_validate(request.model_dump(mode="json") | {"message_id": str(uuid4()), "task_id": str(uuid4())})
    try:
        await transport.adapters["skeptic"].on_message(platform(forged), FakeAgentTools(), [], None, None,
            is_session_bootstrap=False, room_id="private-test-room")
        assert calls == []
        assert sent == []
    finally:
        await transport.close()
