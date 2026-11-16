"""BAND 9.1.0 transport using actual SDK lifecycle and REST models.

Only a locally registered pending task may trigger a provider. Unrelated room
messages cannot invoke tools or spend money. Every send explicitly mentions its
recipient and requires a matching platform receipt. No write retry is enabled.
"""

import asyncio
import json
from contextlib import AsyncExitStack
from time import monotonic

from app.collaboration.ledger import digest


async def send_addressed(rest, room_id, recipient_id, payload, remaining):
    from band.client.rest import ChatMessageRequest
    from band_rest.types import ChatMessageRequestMentionsItem

    content = json.dumps(payload, separators=(",", ":"))
    if len(content.encode()) > 128_000:
        raise ValueError("BAND payload exceeds budget")
    reply = await rest.agent_api_messages.create_agent_chat_message(
        chat_id=room_id,
        message=ChatMessageRequest(
            content=content, mentions=[ChatMessageRequestMentionsItem(id=recipient_id)]
        ),
        request_options={"max_retries": 0, "timeout_in_seconds": remaining},
    )
    if not reply.success or not reply.id or recipient_id not in {r.id for r in reply.recipients}:
        raise ValueError("BAND did not confirm the addressed recipient")
    return reply.id


def adapter_for(session, role):
    from band.core.simple_adapter import SimpleAdapter

    class CaseAdapter(SimpleAdapter):
        @property
        def judges_turns(self):
            return False  # No implicit model repair/retry loop.

        async def on_message(
            self, msg, tools, history, participants_msg, contacts_msg, *, is_session_bootstrap, room_id
        ):
            await session.receive(role, msg, room_id)
            await tools.no_reply("Case transport completed; no model-generated platform actions allowed.")

    return CaseAdapter()


class BandSession:
    def __init__(self, room_id, identities, keys, handlers):
        if set(identities) != {"controller", "scout", "skeptic", "builder"} or set(keys) != set(identities):
            raise ValueError("Four registered case identities required")
        if len(set(identities.values())) != 4:
            raise ValueError("Case identities must be distinct")
        self.room_id, self.identities, self.keys, self.handlers = room_id, identities, keys, handlers
        self.pending = {}
        self.rest = {}
        self.stack = AsyncExitStack()

    async def __aenter__(self):
        from band import Agent
        from band.client.rest import AsyncRestClient, aclose_rest_client
        from band.runtime.agentconfig import AgentConfig
        from band.runtime.contacts import ContactEventConfig

        try:
            for role in self.identities:
                rest = AsyncRestClient(api_key=self.keys[role])
                self.rest[role] = rest
                self.stack.push_async_callback(aclose_rest_client, rest)
                agent = Agent.create(
                    adapter=adapter_for(self, role),
                    agent_id=self.identities[role],
                    api_key=self.keys[role],
                    contact_config=ContactEventConfig(),
                    config=AgentConfig(auto_subscribe_existing_rooms=False),
                )
                await self.stack.enter_async_context(agent)
                await agent.runtime.link.subscribe_room(self.room_id)
            return self
        except BaseException:
            await self.stack.aclose()
            raise

    async def __aexit__(self, *args):
        await self.stack.aclose()

    async def request(self, task, context):
        envelope = {"kind": "case_request", "task": task.model_dump(mode="json"), "context": context}
        future = asyncio.get_running_loop().create_future()
        if task.task_id in self.pending:
            raise ValueError("Duplicate dispatch; no automatic retry")
        item = {
            "task": task,
            "envelope": envelope,
            "future": future,
            "executed": False,
            "execution": None,
            "deadline": monotonic() + task.remaining_seconds,
            "reply": None,
            "request_message": None,
            "reply_message": None,
        }
        self.pending[task.task_id] = item
        try:
            async with asyncio.timeout(task.remaining_seconds):
                item["request_message"] = await send_addressed(
                    self.rest[task.sender],
                    self.room_id,
                    self.identities[task.recipient],
                    envelope,
                    task.remaining_seconds,
                )
                output = await future
        finally:
            execution = item["execution"]
            if execution is not None and not execution.done():
                execution.cancel()
                await asyncio.gather(execution, return_exceptions=True)
        return output, {
            "room": self.room_id,
            "request": item["request_message"],
            "reply": item["reply_message"],
        }

    async def receive(self, role, message, room_id):
        if room_id != self.room_id or message.room_id != self.room_id or len(message.content) > 128_000:
            return
        try:
            payload = json.loads(message.content)
            if not isinstance(payload, dict):
                return
            task_id = (
                payload.get("task", {}).get("task_id")
                if payload.get("kind") == "case_request"
                else payload.get("task_id")
            )
            item = self.pending.get(task_id)
            if not item or item["future"].done():
                return
            task = item["task"]
            if payload.get("kind") == "case_request":
                if (
                    role != task.recipient
                    or message.sender_id != self.identities[task.sender]
                    or digest(payload) != digest(item["envelope"])
                    or item["executed"]
                ):
                    return
                item["executed"] = True  # Provider failure still consumes the attempt.
                try:
                    remaining = item["deadline"] - monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Task expired before dispatch")
                    bounded_task = task.model_copy(update={"remaining_seconds": remaining})
                    item["execution"] = asyncio.create_task(
                        self.handlers[role](bounded_task, payload["context"])
                    )
                    output = await item["execution"]
                    item["reply"] = {"kind": "case_reply", "task_id": task.task_id, "output": output}
                    item["reply_message"] = await send_addressed(
                        self.rest[role],
                        self.room_id,
                        self.identities[task.sender],
                        item["reply"],
                        max(0.001, item["deadline"] - monotonic()),
                    )
                except Exception as exc:  # noqa: BLE001 — sanitized session boundary, no retry.
                    if not item["future"].done():
                        item["future"].set_exception(ValueError("BAND role execution or reply unavailable"))
                    del exc
            elif payload.get("kind") == "case_reply":
                if (
                    role != task.sender
                    or message.sender_id != self.identities[task.recipient]
                    or item["reply"] is None
                    or digest(payload) != digest(item["reply"])
                ):
                    return
                item["reply_message"] = message.id
                item["future"].set_result(payload["output"])
        except (ValueError, TypeError, AttributeError):
            return
