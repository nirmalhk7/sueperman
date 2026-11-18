"""Authenticated addressed BAND exchange for live case tasks, without purchase payloads."""

import asyncio
from datetime import UTC, datetime, timedelta
from functools import partial
from typing import Literal
from uuid import uuid4

from band.core import SimpleAdapter
from band.runtime.formatters import strip_leading_mentions
from pydantic import AwareDatetime, Field, model_validator

from app.collaboration.contracts import CaseResult, CaseTask, Strict
from app.diwali.band_bridge import BandTransport

ALIASES = {"controller": "manager", "scout": "researcher", "skeptic": "skeptic", "builder": "builder"}
PROVIDERS = {"researcher": "agent37", "skeptic": "lyzr", "builder": "lyzr"}


class LiveWire(Strict):
    schema_version: Literal[1] = 1
    message_id: str = Field(min_length=1, max_length=100)
    sender: Literal["manager", "researcher", "skeptic", "builder"]
    recipient: Literal["manager", "researcher", "skeptic", "builder"]
    task: CaseTask
    binding: str = Field(pattern=r"^[a-f0-9]{64}$")
    deadline_at: AwareDatetime
    result: CaseResult | None = None

    @property
    def case_id(self):
        return self.task.case_id

    @model_validator(mode="after")
    def route(self):
        if self.task.mode != "live":
            raise ValueError("Only live tasks allowed")
        expected = ((ALIASES[self.task.sender], ALIASES[self.task.recipient]) if self.result is None
                    else (ALIASES[self.task.recipient], "manager"))
        if (self.sender, self.recipient) != expected:
            raise ValueError("Incorrect addressed task route")
        return self


class LiveAdapter(SimpleAdapter[list]):
    def __init__(self, role, identities, room_id, resolve, send, *, handlers, clock=None, reviewer=None, authorize=None):
        super().__init__(emit=(), capabilities=())
        self.role, self.identities, self.room_id = role, identities, room_id
        self.send, self.handlers, self.authorize = send, handlers, authorize
        self.clock = clock or (lambda: datetime.now(UTC))
        self.seen = {}
        self.inbox: asyncio.Queue = asyncio.Queue(maxsize=12)
        self.rejections = []

    async def on_started(self, agent_name, agent_description):
        if self.platform is None or self.platform.agent_id != self.identities[self.role]:
            raise ValueError("Configured live identity differs from SDK identity")
        await super().on_started(agent_name, agent_description)

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *, is_session_bootstrap, room_id):
        try:
            if (room_id != self.room_id or msg.room_id != self.room_id or msg.sender_type != "Agent"
                    or msg.message_type != "text" or len(msg.content.encode()) > 65536):
                raise ValueError("Unexpected live platform route")
            wire = LiveWire.model_validate_json(strip_leading_mentions(msg.content, only_first=True))
            if (wire.recipient != self.role or msg.sender_id != self.identities[wire.sender]
                    or self.clock() >= wire.deadline_at):
                raise ValueError("Untrusted or expired live task")
            if self.authorize is not None:
                self.authorize(wire)
            canonical = wire.model_dump_json()
            if wire.message_id in self.seen:
                if self.seen[wire.message_id] != canonical:
                    raise ValueError("Conflicting live delivery")
                return
            self.seen[wire.message_id] = canonical
            if self.role == "manager":
                self.inbox.put_nowait((wire, msg.id))
            else:
                try:
                    result = await self.handlers[self.role](wire.task)
                except Exception:  # noqa: BLE001 - sanitize provider errors at the message boundary
                    result = CaseResult.model_validate({"task_id": wire.task.task_id, "case_id": wire.task.case_id,
                        "revision": wire.task.revision, "provider": PROVIDERS[self.role], "mode": "live",
                        "status": "failed", "source_refs": []})
                await self.send(LiveWire(message_id=str(uuid4()), sender=self.role, recipient="manager",
                    task=wire.task, binding=wire.binding, deadline_at=wire.deadline_at, result=result))
        except (ValueError, KeyError, TypeError, asyncio.QueueFull):
            self.rejections.append("INVALID_LIVE_DELIVERY")
        finally:
            tools.turn.settle()


class LiveTransport(BandTransport):
    def __init__(self, credentials, handlers):
        super().__init__(credentials, adapter_factory=partial(LiveAdapter, handlers=handlers), cycle_seconds=90)
        self.live_active = {}
        self.receipts = []

    def authorize(self, wire):
        expected = self.live_active.get(wire.task.task_id)
        if expected is None or wire.task != expected.task or wire.binding != expected.binding:
            raise ValueError("Live task differs from persisted coordinator intent")
        if wire.deadline_at != expected.deadline_at:
            raise ValueError("Changed live deadline")
        if wire.result is None and wire != expected:
            raise ValueError("Changed live request")

    async def exchange(self, task, binding):
        if task.task_id in self.dispatched or len(self.dispatched) >= 3:
            raise ValueError("Live transport budget exhausted")
        self.dispatched.add(task.task_id)
        wire = LiveWire.model_validate({"message_id": str(uuid4()), "sender": ALIASES[task.sender], "recipient": ALIASES[task.recipient],
            "task": task, "binding": binding, "deadline_at": self.clock() + timedelta(milliseconds=task.remaining_ms)})
        self.live_active[task.task_id] = wire
        try:
            async with asyncio.timeout(task.remaining_ms / 1000):
                request_id = await self.adapters[wire.sender].send(wire)
                response, response_id = await self.adapters["manager"].inbox.get()
            if response.task != task or response.binding != binding or response.result is None:
                raise ValueError("Live response does not match request")
            self.receipts.append({"provider": "band", "role": task.recipient,
                "request_id": request_id, "result_id": response_id})
            return response.result
        finally:
            self.live_active.pop(task.task_id, None)
