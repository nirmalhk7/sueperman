"""Pinned BAND custom adapter. SDK metadata authenticates the application wire.

This module does no work on import. Sending and agent startup are explicit,
operator-authorized operations. Tests at the SDK HTTP boundary are not live proof.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from band.client.rest import AsyncRestClient, ChatMessageRequest
from band.client.streaming.client import WebSocketClient
from band.core import SimpleAdapter
from band.runtime.formatters import strip_leading_mentions
from band_rest import ChatMessageRequestMentionsItem

from app.diwali.core import CaseInput, actor_reply, digest, failure_reply
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
                 clock: Callable[[], datetime] | None = None, reviewer=None, authorize=None):
        super().__init__(emit=(), capabilities=())
        if set(identities) != {"manager", "researcher", "skeptic", "builder"} or len(set(identities.values())) != 4:
            raise ValueError("Four distinct BAND identities required")
        if role not in identities:
            raise ValueError("Unknown actor identity")
        self.role, self.identities, self.room_id = role, dict(identities), room_id
        self.reviewer = reviewer
        self.authorize = authorize
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
            if self.authorize is not None:
                self.authorize(wire)
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
                if self.role == "skeptic" and self.reviewer:
                    try:
                        result = await self.reviewer.review(wire, context)
                    except Exception:  # noqa: BLE001 -- enabled provider failure is terminal and sanitized
                        result = failure_reply(wire, "INVALID_RESULT")
                else:
                    result = actor_reply(wire, context)
                result = Message.model_validate(result.model_dump(mode="json") | {"sent_at": self.clock()})
                await self.send(result)
            tools.turn.settle()
        except (ValueError, KeyError, asyncio.QueueFull):
            self.rejections.append("INVALID_PLATFORM_MESSAGE")
            tools.turn.settle()


class SingleAttemptWebSocket(WebSocketClient):
    """Pinned 8.1.0 lifecycle hooks: one handshake, no autonomous reconnect.

    These two private hooks are an explicit version-bound compatibility seam.
    Contract tests exercise the SDK entry/exit loop at its socket boundary.
    """

    async def _resolve_failed_connect_attempt(self, exc, epoch):
        raise exc

    def _finalize_successful_connect(self, epoch):
        super()._finalize_successful_connect(epoch)
        client = self.client
        if client is None:
            raise ValueError("SDK socket missing after successful connect")
        client.auto_reconnect = False


class SingleAttemptLink:
    """Build the pinned SDK link with bounded HTTP and WebSocket operations."""

    @staticmethod
    def create(**kwargs):
        from band.platform import BandLink

        class Link(BandLink):
            async def connect(self):
                if self._connecting or self._ws is not None:
                    return
                self._connecting = True
                ws = SingleAttemptWebSocket(self.ws_url, self.api_key, self.agent_id,
                    on_reconnect=self._on_reconnected, on_disconnect=self._on_disconnected,
                    conflict_policy=self.conflict_policy)
                try:
                    await ws.__aenter__()
                    await self._join_agent_control_channel(ws)
                    self._ws = ws
                    self._is_connected = not ws.transport_ended
                except BaseException:
                    await ws.__aexit__(None, None, None)
                    raise
                finally:
                    self._connecting = False

        return Link(**kwargs)


class BandTransport:
    """One run, four SDK hosts, immutable actor input, no database access.

    prepare() allocates local resources only. Entering starts authenticated
    connections; callers must persist intent before exchange(). No retry/fallback.
    """

    mode = "band"

    def __init__(self, credentials, *, reviewer=None, adapter_factory=None, cycle_seconds=10):
        from importlib.metadata import version

        if version("band-sdk") != "8.1.0" or version("band-sdk-core") != "6.1.1":
            raise ValueError("Unverified BAND dependency version")
        actors = credentials.get("actors", {})
        roles = {"manager", "researcher", "skeptic", "builder"}
        if (set(credentials) != {"room_id", "actors"} or set(actors) != roles
                or not isinstance(credentials["room_id"], str) or not credentials["room_id"]):
            raise ValueError("Four private BAND identities and a room required")
        for value in actors.values():
            if (set(value) != {"agent_id", "api_key"}
                    or not isinstance(value["agent_id"], str) or not value["agent_id"]
                    or not isinstance(value["api_key"], str) or not value["api_key"]):
                raise ValueError("Incomplete BAND actor credentials")
        self.identities = {role: value["agent_id"] for role, value in actors.items()}
        if len(set(self.identities.values())) != 4:
            raise ValueError("Four distinct BAND identities required")
        self._credentials = credentials
        self.reviewer = reviewer
        if not 1 <= cycle_seconds <= 90:
            raise ValueError("Bounded actor cycle required")
        self.adapter_factory = adapter_factory or CaseBandAdapter
        self.cycle_seconds = cycle_seconds
        self.room_id = credentials["room_id"]
        self.clock = lambda: datetime.now(UTC)
        self.contexts: dict = {}
        self.adapters: dict = {}
        self.agents: list = []
        self.clients: list = []
        self.unused_rest: list = []
        self.dispatched: set = set()
        self.active: dict = {}
        self.sent: dict = {}
        self.last_receipt = None
        self.ready = False

    def prepare(self):
        import httpx
        from band import Agent, AgentConfig, SessionConfig
        from band.config.settings import DEFAULT_REST_URL, DEFAULT_WS_URL
        from band.core.types import ConflictPolicy
        from band.runtime.platform_runtime import PlatformRuntime

        if self.adapters:
            raise ValueError("BAND run already prepared")

        async def no_http_retry(response):
            # Raise before the generated SDK sees a retryable response.
            if response.status_code >= 300:
                response.raise_for_status()

        def link_factory(**kwargs):
            link = SingleAttemptLink.create(**kwargs)
            self.unused_rest.append(link.rest)
            link.rest = clients[kwargs["agent_id"]][1]
            return link

        clients = {}
        for role, actor in self._credentials["actors"].items():
            http = httpx.AsyncClient(timeout=10, follow_redirects=False,
                event_hooks={"response": [no_http_retry]})
            self.clients.append(http)
            rest = AsyncRestClient(api_key=actor["api_key"], base_url=DEFAULT_REST_URL,
                httpx_client=http, follow_redirects=False)
            clients[actor["agent_id"]] = (http, rest)

            async def send(wire, rest=rest):
                count = self.sent.get(wire.case_id, 0)
                if count >= 12:
                    raise ValueError("BAND application message budget exhausted")
                self.sent[wire.case_id] = count + 1
                return await send_wire(rest, self.room_id, wire, self.identities, timeout=10)

            adapter = self.adapter_factory(role, self.identities, self.room_id,
                lambda wire: self.contexts[wire.case_id], send, clock=self.clock, reviewer=self.reviewer, authorize=self.authorize)
            self.adapters[role] = adapter
            runtime = PlatformRuntime(actor["agent_id"], actor["api_key"],
                ws_url=DEFAULT_WS_URL, rest_url=DEFAULT_REST_URL,
                config=AgentConfig(single_instance=True, conflict_policy=ConflictPolicy.REJECT),
                session_config=SessionConfig(max_message_retries=1, enable_context_hydration=False,
                    consume_all_queued=False, enable_working_state=False,
                    report_turn_failures_to_room=False, max_cycle_seconds=self.cycle_seconds), link_factory=link_factory)
            self.agents.append(Agent(runtime=runtime, adapter=adapter))

    async def __aenter__(self):
        self.prepare()
        try:
            async with asyncio.timeout(10):
                await asyncio.gather(*(agent.start() for agent in self.agents))
            self.ready = True
            return self
        except BaseException:
            await self.close()
            raise

    def authorize(self, wire):
        request = self.active.get(wire.task_id)
        if request is None:
            raise ValueError("No active coordinator intent for task")
        if wire.recipient != "manager":
            if wire != request:
                raise ValueError("Request differs from active coordinator intent")
        elif (wire.causation_id != request.message_id or wire.case_id != request.case_id
                or wire.run_id != request.run_id or wire.expected_case_revision != request.expected_case_revision
                or wire.sender != request.recipient):
            raise ValueError("Response differs from active coordinator intent")

    async def exchange(self, message, context):
        if message.message_id in self.dispatched:
            raise ValueError("Task already dispatched; explicit new run required")
        if self.clock() >= message.deadline_at:
            raise TimeoutError("BAND task deadline")
        self.dispatched.add(message.message_id)
        self.contexts[context.case_id] = context
        self.active[message.task_id] = message
        self.last_receipt = None
        try:
            async with asyncio.timeout(min(10, (message.deadline_at - self.clock()).total_seconds())):
                request_id = await self.adapters["manager"].send(message)
                received = await self.adapters["manager"].inbox.get()
            wire = received.wire
            if (wire.task_id != message.task_id or wire.causation_id != message.message_id
                    or received.authenticated_sender != self.identities[message.recipient]):
                raise ValueError("BAND receipt does not match dispatched task")
            self.last_receipt = {"request_id": request_id, "result_id": received.platform_message_id,
                "authenticated_sender": received.authenticated_sender,
                "authenticated_recipient": received.authenticated_recipient}
            if self.reviewer and str(message.task_id) in self.reviewer.receipts:
                self.last_receipt["reviewer"] = dict(self.reviewer.receipts[str(message.task_id)])
            return wire
        finally:
            self.active.pop(message.task_id, None)

    async def close(self):
        from band.client.rest import aclose_rest_client

        stopped = await asyncio.gather(*(agent.stop(timeout=1) for agent in self.agents), return_exceptions=True)
        await asyncio.gather(*(client.aclose() for client in self.clients), return_exceptions=True)
        await asyncio.gather(*(aclose_rest_client(rest) for rest in self.unused_rest), return_exceptions=True)
        self.contexts.clear()
        self.ready = False
        if any(result is not True for result in stopped):
            raise RuntimeError("BAND cleanup incomplete; do not start another run")

    async def __aexit__(self, *args):
        await self.close()
