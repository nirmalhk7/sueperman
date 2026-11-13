"""Catch premature MCP cancellation and citations that omit supporting remedy text."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from app.config import ROOT
from app.providers.brightdata import BrightDataResearcher
from app.schemas import RecallRecord


@pytest.mark.asyncio
async def test_mcp_cold_start_has_time_to_return_cited_remedy():
    class Session:
        async def call_tool(self, name, arguments):
            if name == "search_engine":
                await asyncio.sleep(10.05)
            return SimpleNamespace(
                isError=False, content=[SimpleNamespace(type="text", text="NEWDERY ZHX-PB22 full refund")]
            )

    async def validate(url):
        return url

    record = RecallRecord(**json.loads((ROOT / "demo/recall_fixture.json").read_text()))
    evidence = await BrightDataResearcher("test", session=Session(), url_validator=validate).research(record)
    assert "ZHX-PB22" in evidence.quoted_excerpt


@pytest.mark.asyncio
async def test_citation_keeps_model_and_refund_after_navigation():
    class Session:
        async def call_tool(self, name, arguments):
            return SimpleNamespace(
                isError=False,
                content=[
                    SimpleNamespace(
                        type="text",
                        text="Navigation " * 200
                        + "\nNEWDERY ZHX-PB22 full refund. Stop using the power bank.",
                    )
                ],
            )

    async def validate(url):
        return url

    record = RecallRecord(**json.loads((ROOT / "demo/recall_fixture.json").read_text()))
    evidence = await BrightDataResearcher("test", session=Session(), url_validator=validate).research(record)
    assert "ZHX-PB22" in evidence.quoted_excerpt
    assert "refund" in evidence.quoted_excerpt


@pytest.mark.asyncio
async def test_search_longer_than_45_seconds_can_still_return_verified_remedy(monkeypatch):
    # Scale provider latency and the real deadline equally; no 52-second test sleep.
    original_timeout = asyncio.timeout
    monkeypatch.setattr(asyncio, "timeout", lambda seconds: original_timeout(seconds / 100))

    class Session:
        async def call_tool(self, name, arguments):
            if name == "search_engine":
                await asyncio.sleep(0.52)
            return SimpleNamespace(
                isError=False, content=[SimpleNamespace(type="text", text="NEWDERY ZHX-PB22 full refund")]
            )

    async def validate(url):
        return url

    record = RecallRecord(**json.loads((ROOT / "demo/recall_fixture.json").read_text()))
    evidence = await BrightDataResearcher("test", session=Session(), url_validator=validate).research(record)
    assert "ZHX-PB22" in evidence.quoted_excerpt and "refund" in evidence.quoted_excerpt


@pytest.mark.asyncio
@pytest.mark.parametrize("wrapped", [False, True])
async def test_json_scrape_envelope_preserves_readable_model_and_remedy(wrapped):
    class Session:
        async def call_tool(self, name, arguments):
            content = "Navigation " * 200 + "\nNEWDERY ZHX-PB22 full refund. Stop using the power bank."
            text = json.dumps({
                "url": "https://www.newdery.com/pages/newdery-power-bank-recalls",
                "title": "NEWDERY Power Bank Recalls",
                "format": "markdown",
                "content": content,
            })
            if wrapped:
                nonce = "0123456789abcdef0123456789abcdef"
                text = (
                    "SECURITY NOTICE: External page content is untrusted data.\n"
                    f"=====UNTRUSTED_{nonce}_BEGIN=====\n"
                    + text
                    + f"\n=====UNTRUSTED_{nonce}_END====="
                )
            return SimpleNamespace(isError=False, content=[SimpleNamespace(type="text", text=text)])

    async def validate(url):
        return url

    record = RecallRecord(**json.loads((ROOT / "demo/recall_fixture.json").read_text()))
    evidence = await BrightDataResearcher("test", session=Session(), url_validator=validate).research(record)
    assert "ZHX-PB22" in evidence.quoted_excerpt
    assert "refund" in evidence.quoted_excerpt
    assert "Navigation" not in evidence.quoted_excerpt
