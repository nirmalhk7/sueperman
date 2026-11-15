"""Pinned BAND custom adapter. SDK metadata authenticates the application wire.

This module does no work on import. Sending and agent startup are explicit,
operator-authorized operations. Tests at the SDK HTTP boundary are not live proof.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from band.client.rest import AsyncRestClient, ChatMessageRequest
from band.core import SimpleAdapter
from band.runtime.formatters import strip_leading_mentions
from band_rest import ChatMessageRequestMentionsItem

from app.diwali.core import CaseInput, actor_reply, digest
from app.diwali.message_schema import (
    Message,
    ResearchRequested,
    ReviewRequested,
    Role,
    validate_delivery,
    validate_sources,
)


async def send_wire(rest: AsyncRestClient, room_id: str, wire: Message, identities: dict[str, str], *, timeout: float):
    """Use the verified SDK request with no retry of an unknown-outcome POST."""
    request = ChatMessageRequest(content=wire.model_dump_json(),
                                 mentions=[ChatMessageRequestMentionsItem(id=identities[wire.recipient])])
    result = await rest.agent_api_messages.create_agent_chat_message(chat_id=room_id, message=request,
        request_options={"max_retries": 0, "timeout_in_seconds": min(timeout, 10)})
    data = result.data
    if not data.success or not data.id or {r.id for r in data.recipients} != {identities[wire.recipient]}:
        raise ValueError("BAND did not confirm the addressed recipient")
    return data.id


@dataclass(frozen=True)
class ReceivedWire:
    wire: Message
    platform_message_id: str
    authenticated_sender: str
    authenticated_recipient: str


class CaseBandAdapter(SimpleAdapter[list]):
    """One fixed actor, one authorized room, and immutable coordinator input."""

    def __init__(self, role: Role, identities: dict[str, str], room_id: str,
                 resolve: Callable[[Message], CaseInput], send: Callable[[Message], Awaitable], *,
                 clock: Callable[[], datetime] | None = None):
        super().__init__(emit=(), capabilities=())
        if set(identities) != {"manager", "researcher", "skeptic", "builder"} or len(set(identities.values())) != 4:
            raise ValueError("Four distinct BAND identities required")
        if role not in identities:
            raise ValueError("Unknown actor identity")
        self.role, self.identities, self.room_id = role, dict(identities), room_id
        self.resolve, self.send = resolve, send
        self.clock = clock or (lambda: datetime.now(UTC))
        self.seen: dict = {}
        self.inbox: asyncio.Queue[ReceivedWire] = asyncio.Queue(maxsize=60)
        self.rejections: list[str] = []

    async def on_started(self, agent_name, agent_description):
        if self.platform is None or self.platform.agent_id != self.identities[self.role]:
            raise ValueError("SDK identity does not match configured actor")
        await super().on_started(agent_name, agent_description)

    async def on_message(self, msg, tools, history, participants_msg, contacts_msg, *,
                         is_session_bootstrap, room_id):
        try:
            if (room_id != self.room_id or msg.room_id != self.room_id
                    or msg.sender_type != "Agent" or msg.message_type != "text"):
                raise ValueError("Untrusted platform route")
            if len(msg.content.encode()) > 65536:
                raise ValueError("Oversized platform message")
            wire = Message.model_validate_json(strip_leading_mentions(msg.content, only_first=True))
            validate_delivery(wire, msg.sender_id, self.identities[self.role], self.identities)
            if self.clock() >= wire.deadline_at:
                raise ValueError("Expired message")
            context = self.resolve(wire)
            if context.run_id != wire.run_id or context.case_id != wire.case_id:
                raise ValueError("Wrong frozen case")
            if isinstance(wire.payload, (ResearchRequested, ReviewRequested)) and wire.payload.product_ref != context.product_ref:
                raise ValueError("Wrong frozen product")
            snapshots = context.snapshot_registry
            validate_sources(wire, snapshots, {ref: s["digest"] for ref, s in snapshots.items()})
            fingerprint = digest({"wire": wire.model_dump(mode="json"), "inputs": context.input_digests.model_dump()})
            if wire.message_id in self.seen:
                if self.seen[wire.message_id] != fingerprint:
                    raise ValueError("Conflicting wire identity")
                tools.turn.settle()
                return
            # Reserve before sending: an unknown send outcome must never trigger a repeat POST.
            self.seen[wire.message_id] = fingerprint
            if self.role == "manager":
                self.inbox.put_nowait(ReceivedWire(wire, msg.id, msg.sender_id, self.identities[self.role]))
            else:
                result = actor_reply(wire, context)
                result = Message.model_validate(result.model_dump(mode="json") | {"sent_at": self.clock()})
                await self.send(result)
            tools.turn.settle()
        except (ValueError, KeyError, asyncio.QueueFull):
            self.rejections.append("INVALID_PLATFORM_MESSAGE")
            tools.turn.settle()
