"""Owned, prewarmed Agent37 public worker. Never provisions or tops up funds."""

import asyncio
import base64
import hashlib
import json
import re
import shlex
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from app.diwali.lyzr_review import unique_object
from app.providers.cpsc import CPSCRecallSource
from app.providers.errors import ProviderUnavailable
from app.schemas import ProductInput

WORKER_SOURCE = '''import json, urllib.request, socket, ipaddress
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
addresses = socket.getaddrinfo("www.saferproducts.gov", 443, type=socket.SOCK_STREAM)
if not addresses or any(not ipaddress.ip_address(row[4][0]).is_global for row in addresses):
    raise ValueError("Private source address blocked")
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
url = "https://www.saferproducts.gov/RestWebServices/Recall?ProductName=NEWDERY&format=json"
with opener.open(url, timeout=8) as response:
    if response.status != 200:
        raise ValueError("Official source unavailable")
    body = response.read(262145)
if len(body) > 262144:
    raise ValueError("Official source response too large")
rows = json.loads(body)
if not isinstance(rows, list):
    raise ValueError("Unexpected source format")
print(json.dumps({"reference":"26-792","rows":rows,"worker_sha256":EXPECTED_WORKER_SHA256}))
'''
WORKER_SHA256 = hashlib.sha256(WORKER_SOURCE.encode()).hexdigest()


def worker_command():
    encoded = base64.b64encode(WORKER_SOURCE.encode()).decode()
    launcher = (f"import base64,hashlib;s=base64.b64decode({encoded!r});"
        f"assert hashlib.sha256(s).hexdigest()=={WORKER_SHA256!r};"
        f"exec(compile(s,'pinned-public-worker','exec'),{{'EXPECTED_WORKER_SHA256':{WORKER_SHA256!r}}})")
    return "python3 -c " + shlex.quote(launcher)


class Agent37Worker:
    def __init__(self, api_key, instance_id, *, owned_ids, client=None):
        if not api_key or instance_id not in owned_ids or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", instance_id):
            raise ValueError("An explicitly owned prewarmed instance is required")
        self._api_key, self.instance_id, self.client = api_key, instance_id, client
        self.attempted: set = set()

    async def request(self, method, endpoint, *, payload=None):
        control = f"https://api.agent37.com/v1/instances/{self.instance_id}"
        execution = f"https://sandbox.agent37.app/v1/instances/{self.instance_id}/exec"
        if (method, endpoint) not in {("GET", control), ("DELETE", control), ("POST", execution)}:
            raise ValueError("Unapproved owned-instance endpoint")
        own = self.client is None
        http = self.client or httpx.AsyncClient(timeout=10, follow_redirects=False)
        headers = ({"X-Agent37-Key": self._api_key} if endpoint.startswith("https://sandbox.agent37.app/")
                   else {"Authorization": f"Bearer {self._api_key}"})
        try:
            async with asyncio.timeout(10):
                async with http.stream(method, endpoint, json=payload, headers=headers,
                        follow_redirects=False) as response:
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > 524288:
                            raise ValueError("Oversized Agent37 result")
                    if response.status_code == 404 and method == "GET":
                        return {"not_found": True}
                    if response.status_code != 200:
                        raise ValueError("Agent37 operation unavailable; no retry")
                    result = json.loads(body, object_pairs_hook=unique_object)
                    if not isinstance(result, dict):
                        raise TypeError("Malformed Agent37 result")
                    return result
        except (httpx.HTTPError, TimeoutError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("Agent37 operation failed; no retry") from exc
        finally:
            if own:
                await http.aclose()

    async def run(self, run_id, case_id):
        task = f"sueperman-{run_id}-{case_id}"
        if len(task) > 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", task):
            raise ValueError("Invalid bounded task correlation")
        if task in self.attempted:
            raise ValueError("Worker already attempted; reconcile before another run")
        self.attempted.add(task)
        result = await self.request("POST", f"https://sandbox.agent37.app/v1/instances/{self.instance_id}/exec",
            payload={"command": worker_command(), "background": False, "name": task})
        if (type(result.get("exit_code")) is not int or result["exit_code"] != 0
                or result.get("truncated") is not False or not isinstance(result.get("stdout"), str)):
            raise ValueError("Worker did not return a complete successful result")
        try:
            output = json.loads(result["stdout"], object_pairs_hook=unique_object)
            if (set(output) != {"reference", "rows", "worker_sha256"} or output["reference"] != "26-792"
                    or output["worker_sha256"] != WORKER_SHA256 or not isinstance(output["rows"], list)):
                raise ValueError("Worker pin or source contract mismatch")

            class CapturedOfficialRows:
                async def get(self, url, **kwargs):
                    if url != "https://www.saferproducts.gov/RestWebServices/Recall":
                        raise ValueError("Unexpected normalization source")
                    return httpx.Response(200, json=output["rows"], request=httpx.Request("GET", url))

            with TemporaryDirectory(prefix="sueperman-worker-normalize-") as folder:
                source = CPSCRecallSource(client=CapturedOfficialRows(), cache_dir=Path(folder))
                records = await source.search(ProductInput(product_name="Power bank", brand="NEWDERY"))
            matches = [record for record in records if record.reference == "26-792"]
            if source.truncated or len(matches) != 1 or matches[0].models != ["ZHX-PB22"]:
                raise ValueError("Unsupported remote source result")
            return {"record": matches[0].model_dump(mode="json"), "worker_sha256": WORKER_SHA256,
                "instance_id": self.instance_id, "task_name": task, "execution_mode": "agent37",
                "stdout_sha256": hashlib.sha256(result["stdout"].encode()).hexdigest()}
        except (KeyError, TypeError, ProviderUnavailable, json.JSONDecodeError) as exc:
            raise ValueError("Invalid remote public evidence") from exc

    async def delete_and_confirm(self):
        url = f"https://api.agent37.com/v1/instances/{self.instance_id}"
        result = await self.request("DELETE", url)
        if result.get("id") != self.instance_id or result.get("deleted") is not True:
            raise ValueError("Instance deletion not confirmed")
        after = await self.request("GET", url)
        if after != {"not_found": True}:
            raise ValueError("Owned instance still exists; cleanup incomplete")
        return True
