"""BAND metadata, task identity and duplicate delivery protect real provider calls."""

import importlib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.collaboration.contracts import CaseResult, CaseTask


def module():
    try:
        return importlib.import_module("app.collaboration.live_transport")
    except ModuleNotFoundError:
        pytest.fail("Live addressed transport is not implemented")


async def test_authenticated_task_executes_once_and_returns_addressed_result():
    live = module()
    task = CaseTask(case_id="case", task_id="task", revision=1, sender="controller", recipient="scout",
        kind="source_investigation", deduplication_key="one", remaining_ms=20000, mode="live")
    wire = live.LiveWire(message_id="message", sender="manager", recipient="researcher", task=task,
        binding="a" * 64, deadline_at=datetime.now(UTC) + timedelta(seconds=20))
    invoked, sent = [], []

    async def handler(value):
        invoked.append(value)
        return CaseResult(task_id="task", case_id="case", revision=1, provider="agent37", mode="live",
                          status="completed", findings=[], source_refs=[])

    async def send(value):
        sent.append(value)

    adapter = live.LiveAdapter("researcher", {r:r for r in ("manager", "researcher", "skeptic", "builder")},
        "room", lambda _: None, send, handlers={"researcher": handler}, authorize=lambda _: None)
    message = SimpleNamespace(room_id="room", sender_type="Agent", message_type="text", sender_id="manager",
        content=wire.model_dump_json(), id="platform-message")
    tools = SimpleNamespace(turn=SimpleNamespace(settle=lambda: None))
    for _ in range(2):
        await adapter.on_message(message, tools, None, None, None, is_session_bootstrap=False, room_id="room")
    assert len(invoked) == 1
    assert len(sent) == 1
    assert sent[0].sender == "researcher" and sent[0].recipient == "manager"
    assert sent[0].result.provider == "agent37"


@pytest.mark.parametrize("fault", ["sender", "room", "expired", "changed-task"])
async def test_foreign_or_changed_task_never_executes_provider(fault):
    live = module()
    task = CaseTask(case_id="case", task_id="task", revision=1, sender="controller", recipient="scout",
        kind="source_investigation", deduplication_key="one", remaining_ms=20000, mode="live")
    wire = live.LiveWire(message_id="message", sender="manager", recipient="researcher", task=task,
        binding="a" * 64, deadline_at=datetime.now(UTC) + timedelta(seconds=-1 if fault == "expired" else 20))
    invoked = []

    async def handler(value):
        invoked.append(value)

    async def send(value):
        raise AssertionError("No reply to an unauthenticated task")

    def authorize(value):
        if fault == "changed-task":
            raise ValueError("Coordinator input changed")

    adapter = live.LiveAdapter("researcher", {r:r for r in ("manager", "researcher", "skeptic", "builder")},
        "room", lambda _: None, send, handlers={"researcher": handler}, authorize=authorize)
    message = SimpleNamespace(room_id="other" if fault == "room" else "room", sender_type="Agent",
        message_type="text", sender_id="intruder" if fault == "sender" else "manager",
        content=wire.model_dump_json(), id="platform-message")
    tools = SimpleNamespace(turn=SimpleNamespace(settle=lambda: None))
    await adapter.on_message(message, tools, None, None, None, is_session_bootstrap=False, room_id="room")
    assert not invoked
    assert adapter.rejections


async def test_prepared_live_sender_reaches_sdk_http_boundary_once():
    import httpx
    import respx
    from band_rest.core.api_error import ApiError

    live = module()
    credentials = {"room_id": "room", "actors": {role: {"agent_id": role, "api_key": role + "-key"}
        for role in ("manager", "researcher", "skeptic", "builder")}}
    transport = live.LiveTransport(credentials, {})
    transport.prepare()
    task = CaseTask(case_id="case", task_id="task", revision=1, sender="controller", recipient="scout",
        kind="source_investigation", deduplication_key="one", remaining_ms=20000, mode="live")
    wire = live.LiveWire(message_id="message", sender="manager", recipient="researcher", task=task,
        binding="a" * 64, deadline_at=datetime.now(UTC) + timedelta(seconds=20))
    try:
        with respx.mock as router:
            route = router.post(url__regex=r".*/api/v1/agent/chats/room/messages").respond(503,
                json={"error": {"code": "service_unavailable", "message": "unavailable", "request_id": "test"}})
            with pytest.raises((ApiError, httpx.HTTPStatusError)):
                await transport.adapters["manager"].send(wire)
            assert route.call_count == 1
            import json
            sent = json.loads(route.calls[0].request.content)["message"]
            assert sent["mentions"] == [{"id": "researcher"}]
            assert live.LiveWire.model_validate_json(sent["content"]) == wire
    finally:
        await transport.close()
