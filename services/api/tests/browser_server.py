"""Test-only vendor boundaries for the real public workspace browser suite."""
import json
from pathlib import Path

import httpx

from app.collaboration import live
from app.collaboration.live_providers import PUBLIC_WORKER_SHA256
from app.config import ROOT

ROWS = json.loads((ROOT / "services/api/tests/fixtures/cpsc-live.json").read_text())
OriginalClient = httpx.AsyncClient


def response(request):
    host, path = request.url.host, request.url.path
    if host == "www.saferproducts.gov":
        return httpx.Response(200, json=ROWS)
    if host == "api.agent37.com" and request.method == "POST" and path == "/v1/instances":
        return httpx.Response(201, json={"id": "owned-test", "status": "running"})
    if host == "api.agent37.com" and request.method == "DELETE":
        return httpx.Response(200, json={"id": "owned-test", "deleted": True})
    if host == "sandbox.agent37.app" and path.endswith("/exec"):
        return httpx.Response(200, json={"exit_code": 0, "truncated": False, "stderr": "", "stdout":
            json.dumps({"rows": ROWS, "worker_sha256": PUBLIC_WORKER_SHA256})})
    if host == "agent-prod.studio.lyzr.ai":
        payload = json.loads(request.content)
        context = json.loads(payload["message"])
        task = context["task"]
        output = ({"review_note": "Compare the exact identifier with the supplied notice.",
            "evidence_refs": task["source_refs"], "requested_fields": [],
            "uncertainty": context["product"].get("model_number") != "ZHX-PB22"}
            if payload["agent_id"] == "reviewer" else {"schema_version": 1,
            **{k: task[k] for k in ("case_id", "task_id", "revision")}, "provider": "lyzr", "mode": "live",
            **context["validated_review"]})
        return httpx.Response(200, json={"response": json.dumps(output)})
    raise AssertionError("Unregistered external browser-test request")


class OfflineClient(OriginalClient):
    def __init__(self, *args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(response)
        super().__init__(*args, **kwargs)


class HttpBoundaryTransport:
    def __init__(self, credentials, handlers):
        self.handlers, self.receipts = handlers, []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def exchange(self, task, binding):
        self.receipts.append({"provider": "band", "role": task.recipient})
        return await self.handlers[{"scout": "researcher", "skeptic": "skeptic", "builder": "builder"}[task.recipient]](task)


httpx.AsyncClient = OfflineClient
live.LiveTransport = HttpBoundaryTransport
# Keep cache bytes in the disposable database folder.
from app.providers.cpsc import CPSCRecallSource

original_init = CPSCRecallSource.__init__
def isolated_init(self, *args, **kwargs):
    import os
    kwargs.setdefault("cache_dir", Path(os.environ["LIVE_BROWSER_CONTROL"]).parent / "cache")
    original_init(self, *args, **kwargs)
CPSCRecallSource.__init__ = isolated_init
from app.main import app  # noqa: F401 - ASGI entry point
