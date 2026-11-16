"""Pinned public-evidence worker; no Agent37 lifecycle is inferred from local use."""

import asyncio
import hashlib
import json
import socket
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from app.providers.cpsc import CPSCRecallSource
from app.providers.errors import ProviderUnavailable
from app.schemas import ProductInput
from app.security.source_policy import validate_public_url


async def research_public(reference, *, client=None):
    if reference != "26-792":
        raise ValueError("Only the approved supported public recall may be queried")
    own = client is None
    http = client or httpx.AsyncClient(timeout=8, follow_redirects=False)

    class BoundedRead:
        async def get(self, url, *, params, **kwargs):
            if url != "https://www.saferproducts.gov/RestWebServices/Recall" or params != {"ProductName": "NEWDERY", "format": "json"}:
                raise ValueError("Unapproved public query")
            addresses = await asyncio.to_thread(socket.getaddrinfo, "www.saferproducts.gov", 443,
                                                type=socket.SOCK_STREAM)
            validate_public_url(url, frozenset({"www.saferproducts.gov"}),
                                list({str(row[4][0]) for row in addresses}))
            async with http.stream("GET", url, params=params, timeout=8, follow_redirects=False) as response:
                # Fail before the V1 provider's optional GET retry branch.
                response.raise_for_status()
                if response.status_code != 200:
                    raise ValueError("Public source redirect rejected")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > 262144:
                        raise ValueError("Oversized official-source response")
                return httpx.Response(200, content=bytes(body), request=response.request)

    try:
        async with asyncio.timeout(10):
            with TemporaryDirectory(prefix="sueperman-public-worker-") as folder:
                source = CPSCRecallSource(client=BoundedRead(), cache_dir=Path(folder))
                records = await source.search(ProductInput(product_name="Power bank", brand="NEWDERY"))
        matches = [record for record in records if record.reference == reference]
        if source.truncated or len(matches) != 1:
            raise ValueError("Supported source missing or ambiguous")
        record = matches[0]
        if record.models != ["ZHX-PB22"] or record.mode != "live":
            raise ValueError("Official identifiers unsupported; review required")
        payload = record.model_dump(mode="json")
        return {"record": payload, "record_sha256": hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "source_provider": "cpsc", "execution_mode": "local_worker"}
    except (httpx.HTTPError, ProviderUnavailable, TimeoutError) as exc:
        raise ValueError("Public evidence unavailable; no retry") from exc
    finally:
        if own:
            await http.aclose()
