"""Real SDK/API interfaces exercised with isolated synthetic transports; not live proof."""

import json
from types import SimpleNamespace

import httpx
import pytest

from app.collaboration.contracts import CaseTask


def task(role="builder"):
    return CaseTask(
        case_id="case",
        task_id="task",
        revision="a" * 64,
        sender="skeptic" if role == "builder" else "scout",
        recipient=role,
        task_kind="case_board_construction" if role == "builder" else "counterexample_review",
        deduplication_key="task",
        allowed_capabilities=["read_supplied_evidence"],
        source_refs=["26-792"],
        remaining_seconds=10,
        mode="live",
    )


def result(role="builder"):
    return {
        "task_id": "task",
        "case_id": "case",
        "revision": "a" * 64,
        "provider": "lyzr" if role == "builder" else "adal",
        "role": role,
        "mode": "live",
        "status": "completed",
        "findings": [],
        "source_refs": ["26-792"],
    }


@pytest.mark.asyncio
async def test_lyzr_v3_preserves_session_and_sends_only_bounded_context():
    from app.collaboration.runtime_adapters import LyzrBuilder

    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        assert request.headers["x-api-key"] == "synthetic-key"
        return httpx.Response(200, json={"response": json.dumps(result())})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        adapter = LyzrBuilder(
            "synthetic-key",
            "https://agent-prod.studio.lyzr.ai/v3/inference/chat/",
            "agent",
            "synthetic-user",
            "v3_inference",
            client,
        )
        for _ in range(2):
            answer = await adapter.review(task(), {"evidence": [], "prior": result("skeptic")})
            assert answer.provider == "lyzr"
    assert sent[0]["session_id"] == sent[1]["session_id"]
    assert set(sent[0]) == {"agent_id", "user_id", "session_id", "message"}
    assert "synthetic-key" not in sent[0]["message"]


@pytest.mark.asyncio
async def test_lyzr_does_not_retry_or_follow_redirects():
    from app.collaboration.runtime_adapters import LyzrBuilder

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(302, headers={"location": "https://evil.example/steal"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        adapter = LyzrBuilder(
            "secret",
            "https://agent-prod.studio.lyzr.ai/v3/agent/agent/chat",
            "agent",
            "synthetic-user",
            "v3_agent",
            client,
        )
        with pytest.raises(ValueError, match="Builder unavailable"):
            await adapter.review(task(), {})
    assert len(requests) == 1


@pytest.mark.asyncio
async def test_adal_actual_options_wire_deny_callback_and_validate_final_result(tmp_path):
    pytest.importorskip("adal_agent_sdk")
    from app.collaboration.runtime_adapters import AdalSkeptic

    options = []

    class Client:
        session_id = "synthetic-session"

        def __init__(self, opt):
            options.append(opt)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def query(self, prompt):
            assert "skill_bytes" in prompt

        async def receive_events(self, timeout):
            yield {
                "type": "assistant.message.completed",
                "message": {"content": json.dumps(result("skeptic"))},
            }
            yield {"type": "command.completed"}

    adapter = AdalSkeptic("/reviewed/isolated-adal", client_factory=Client)
    answer = await adapter.review(task("skeptic"), {}, "reviewed skill bytes")
    assert answer.provider_reference == "synthetic-session"
    assert options[0].permission_mode == "default"
    assert "Bash" in options[0].disabled_default_tools
    for tool in ["bash", "read_file", "fetch_url", "custom_malicious_tool"]:
        decision = await options[0].can_use_tool(tool, {}, SimpleNamespace(requires_human=False))
        assert decision.behavior == "deny"
    assert options[0].auth_token is None


@pytest.mark.asyncio
async def test_band_uses_real_mention_receipts_and_no_retry():
    pytest.importorskip("band")
    from app.collaboration.band_runtime import send_addressed

    seen = []

    class Messages:
        async def create_agent_chat_message(self, **kwargs):
            seen.append(kwargs)
            return SimpleNamespace(id="message", success=True, recipients=[SimpleNamespace(id="recipient")])

    rest = SimpleNamespace(agent_api_messages=Messages())
    assert await send_addressed(rest, "room", "recipient", {"kind": "synthetic"}, 10) == "message"
    assert seen[0]["message"].mentions[0].id == "recipient"
    assert seen[0]["request_options"]["max_retries"] == 0


@pytest.mark.asyncio
async def test_band_rejects_unconfirmed_recipient_receipt():
    pytest.importorskip("band")
    from app.collaboration.band_runtime import send_addressed

    class Messages:
        async def create_agent_chat_message(self, **kwargs):
            return SimpleNamespace(id="message", success=True, recipients=[])

    with pytest.raises(ValueError, match="recipient"):
        await send_addressed(SimpleNamespace(agent_api_messages=Messages()), "room", "recipient", {}, 10)


@pytest.mark.asyncio
async def test_band_delivery_actually_runs_recipient_once_and_requires_reply():
    pytest.importorskip("band")
    from app.collaboration.band_runtime import BandSession

    ids = {r: r + "-id" for r in ["controller", "scout", "skeptic", "builder"]}
    calls = []

    async def handle(t, context):
        calls.append(context)
        return {"result": result()}

    session = BandSession("room", ids, {r: "synthetic-key" for r in ids}, {"builder": handle})

    class Messages:
        def __init__(self, sender):
            self.sender = sender

        async def create_agent_chat_message(self, chat_id, message, request_options):
            recipient = next(r for r in ids if ids[r] == message.mentions[0].id)
            msg = SimpleNamespace(
                id="msg-" + self.sender, room_id="room", sender_id=ids[self.sender], content=message.content
            )
            import asyncio

            asyncio.get_running_loop().call_soon(
                lambda: asyncio.create_task(session.receive(recipient, msg, "room"))
            )
            return SimpleNamespace(id=msg.id, success=True, recipients=[SimpleNamespace(id=ids[recipient])])

    session.rest = {r: SimpleNamespace(agent_api_messages=Messages(r)) for r in ids}
    answer, receipt = await session.request(task(), {"evidence": []})
    assert answer["result"]["provider"] == "lyzr"
    assert receipt["request"] and receipt["reply"]
    assert len(calls) == 1
    with pytest.raises(ValueError, match="Duplicate"):
        await session.request(task(), {"evidence": []})
    # Unknown sender/case payload cannot spend an invocation.
    await session.receive(
        "builder", SimpleNamespace(room_id="room", sender_id="attacker", content="{}"), "room"
    )
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_band_deadline_cancels_inflight_provider():
    import asyncio

    pytest.importorskip("band")
    from app.collaboration.band_runtime import BandSession

    ids = {r: r + "-id" for r in ["controller", "scout", "skeptic", "builder"]}
    cancelled = asyncio.Event()

    async def handle(t, context):
        try:
            await asyncio.sleep(10)
        finally:
            cancelled.set()

    session = BandSession("room", ids, {r: "synthetic" for r in ids}, {"builder": handle})

    class Messages:
        async def create_agent_chat_message(self, chat_id, message, request_options):
            asyncio.create_task(
                session.receive(
                    "builder",
                    SimpleNamespace(
                        id="request",
                        room_id="room",
                        sender_id=ids["skeptic"],
                        content=message.content,
                    ),
                    "room",
                )
            )
            return SimpleNamespace(
                id="request", success=True, recipients=[SimpleNamespace(id=ids["builder"])]
            )

    session.rest = {"skeptic": SimpleNamespace(agent_api_messages=Messages())}
    with pytest.raises(TimeoutError):
        await session.request(task().model_copy(update={"remaining_seconds": 0.02}), {})
    assert cancelled.is_set(), "Provider must stop when the bounded request expires"
