import asyncio
import hashlib
import os
from datetime import UTC, datetime

from pydantic import BaseModel

from app.providers.errors import ProviderUnavailable
from app.schemas import RecallRecord
from app.security.source_policy import checked_manufacturer_url, official_cpsc


class ResearchEvidence(BaseModel):
    url: str
    publisher: str
    source_type: str = "manufacturer"
    fetched_at: datetime
    quoted_excerpt: str
    content_sha256: str
    authoritative_for: list[str] = ["supplemental_remedy"]


class BrightDataResearcher:
    provider_name = "brightdata"
    mode = "live"

    def __init__(self, token, session=None, url_validator=None):
        self.token, self.session = token, session
        self.validate = url_validator or checked_manufacturer_url

    async def research(self, recall: RecallRecord) -> ResearchEvidence:
        if (
            not self.token
            or not official_cpsc(recall.official_url)
            or recall.reference != "26-792"
            or recall.contact_url != "https://www.newdery.com/pages/newdery-power-bank-recalls"
        ):
            raise ProviderUnavailable("Bright Data requires a supported CPSC-linked manufacturer page")
        try:
            async with asyncio.timeout(45):
                url = await self.validate(recall.contact_url)
                if self.session is not None:
                    text = await self._read(self.session, url)
                else:
                    from mcp import ClientSession, StdioServerParameters
                    from mcp.client.stdio import stdio_client

                    # Only two read-only tools are exposed. No claim browser tool exists.
                    parameters = StdioServerParameters(
                        command="npx",
                        args=["-y", "@brightdata/mcp"],
                        env={
                            "PATH": os.environ.get("PATH", ""),
                            "API_TOKEN": self.token,
                            "TOOLS": "search_engine,scrape_as_markdown",
                        },
                    )
                    with open(os.devnull, "w") as errors:  # noqa: ASYNC230 — local null device; discard provider stderr.
                        async with (
                            stdio_client(parameters, errlog=errors) as (read, write),
                            ClientSession(read, write) as session,
                        ):
                            await session.initialize()
                            text = await self._read(session, url)
            if "ZHX-PB22" not in text or "refund" not in text.casefold():
                raise ValueError("Missing cited model or remedy")
            # Raw web text remains inert evidence; it never changes tool permissions.
            return ResearchEvidence(
                url=url,
                publisher="NEWDERY",
                fetched_at=datetime.now(UTC),
                quoted_excerpt="\n".join(
                    line[:1000]
                    for line in text.splitlines()
                    if "ZHX-PB22" in line or "refund" in line.casefold()
                )[:3000],
                content_sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
        except Exception as exc:
            raise ProviderUnavailable("Bright Data unavailable; official CPSC facts retained") from exc

    async def _read(self, session, url):
        discovery = await session.call_tool(
            "search_engine", arguments={"query": "site:newdery.com ZHX-PB22 recall refund"}
        )
        if discovery.isError:
            raise ValueError("Search failed")
        result = await session.call_tool("scrape_as_markdown", arguments={"url": url})
        if result.isError:
            raise ValueError("Scrape failed")
        return "\n".join(block.text for block in result.content if block.type == "text")
