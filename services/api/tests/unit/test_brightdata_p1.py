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
