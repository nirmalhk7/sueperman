"""Bounded discovery of one source-reviewed case; unknown cases are never inferred."""

import asyncio
import hashlib
import io
import re
from datetime import UTC, date, datetime
from html import unescape
from urllib.parse import unquote

import httpx
from pydantic import BaseModel
from pypdf import PdfReader

from app.matching.normalize import normalize_text
from app.providers.brightdata import ResearchEvidence
from app.providers.errors import ProviderUnavailable
from app.schemas import ProductInput

HOME = "https://www.krogersavingsclubsettlement.com/"
DOCUMENTS = HOME + "important-documents"
NOTICE = "https://angeion-public.s3.amazonaws.com/www.krogersavingsclubsettlement.com/docs/Kirkbride%20v%20Kroger%20-%20Long-Form%20Notice_Final.pdf"
ORDER = "https://angeion-public.s3.amazonaws.com/www.krogersavingsclubsettlement.com/docs/2026.06.25%20DE%20165%20AMENDED%20OPINION%20AND%20ORDER%20-%20Part%201.pdf"
REVIEWED_DOCUMENTS = {
    NOTICE: "c55ef0ea67c0d6f0276d6a28a77a138288fc5a14ed11c600c1a2431b4e823b5b",
    ORDER: "da184d89c8edc12c5238db4a0dba431a39cae46d74e78345c2c37f5fdf8b5dbb",
}


class VerifiedSettlement(BaseModel):
    title: str = "Kirkbride et al. v. The Kroger Co."
    case_number: str = "2:21-cv-00022"
    court: str = "United States District Court for the Southern District of Ohio"
    official_url: str = HOME
    start: date = date(2018, 12, 9)
    end: date = date(2026, 8, 23)
    deadline: date = date(2026, 12, 21)
    simulated: bool = False
    mode: str = "live"
    fetched_at: datetime
    evidence: list[ResearchEvidence]
    qualifying_transaction: str = "Prescription drugs paid in whole or part at Kroger using insurance"
    instructions: str = (
        "Preparation only. Review official terms and personally complete any claim. "
        "Signed attestations, contact details, payment information and any supporting records "
        "must be supplied independently by the user on the official site."
    )
    proof: list[str] = [
        "Purchase/payment records for qualifying insured prescriptions; no medical details needed here",
        "Administrator must determine Known or Unknown Claimant status",
        "Supporting documentation required for total claimed payments of $8,000 or more",
        "Unknown Claimants may be contacted for supporting documentation even below $8,000",
        "User must review geography, exclusions, releases and signature requirements personally",
    ]


class VerifiedSettlementSource:
    provider_name = "verified_public_sources"
    mode = "live"

    def __init__(self, client=None):
        self.client = client
        self._verified = None

    async def search(self, product: ProductInput) -> list[VerifiedSettlement]:
        # Deliberately narrow discovery. Other Kroger-owned pharmacies require a reviewed alias.
        if normalize_text(product.merchant) != "kroger":
            return []
        if self._verified is None:
            self._verified = await self.verify()
        return [self._verified]

    async def verify(self) -> VerifiedSettlement:
        try:
            async with asyncio.timeout(25):
                if self.client is None:
                    async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                        return await self._verify(client)
                return await self._verify(self.client)
        except Exception as exc:
            raise ProviderUnavailable(
                "Settlement primary sources unavailable or changed; no real case shown"
            ) from exc

    async def _verify(self, client):
        # Fixed HTTPS endpoints only; redirects rejected, never followed to user-controlled targets.
        bodies = []
        for url in [HOME, DOCUMENTS, NOTICE, ORDER]:
            response = await client.get(url, timeout=8, follow_redirects=False)
            response.raise_for_status()
            if len(response.content) > 5 * 1024 * 1024:
                raise ValueError("Oversize settlement source")
            if (
                url in REVIEWED_DOCUMENTS
                and hashlib.sha256(response.content).hexdigest() != REVIEWED_DOCUMENTS[url]
            ):
                raise ValueError("Primary document revision requires source/rule review")
            bodies.append(response.content)
        home, documents = (unescape(b.decode()) for b in bodies[:2])
        notice, order = [
            " ".join(" ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(b)).pages).split())
            for b in bodies[2:]
        ]

        def visible_text(html):
            html = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
            return " ".join(re.sub("<[^>]+>", " ", html).split())

        home_text = visible_text(home)
        if not all(
            term in home_text
            for term in ["2:21-cv-00022", "December 21, 2026", "official Settlement Website"]
        ):
            raise ValueError("Administrator terms changed")
        # Documents must be linked from the case administrator, not merely live at an arbitrary host.
        links = {unquote(link) for link in re.findall(r'href="([^"<>]+)"', documents)}
        if not all(unquote(url) in links for url in [NOTICE, ORDER]):
            raise ValueError("Court/notice provenance link missing")
        if not all(
            term in notice
            for term in [
                "2:21-cv-00022",
                "December 9, 2018",
                "August 23, 2026",
                "DECEMBER 21, 2026",
                "using their insurance",
                "$8,000",
                "Unknown Claimant",
            ]
        ):
            raise ValueError("Notice terms changed")
        if not all(
            term in order
            for term in [
                "2:21-cv-00022",
                "AMENDED OPINION",
                "GRANTS",
                "Angeion",
                "prescription drugs from Kroger using their insurance",
            ]
        ):
            raise ValueError("Court cross-check failed")
        observed = datetime.now(UTC)
        excerpts = [
            home_text[home_text.index("This is the official Settlement Website") :][:1500],
            visible_text(documents)[:1800],
            notice[
                notice.index("Who Is Included?") : notice.index(
                    "What Does The Class Action Settlement Provide?"
                )
            ]
            + "\n[…]\n"
            + notice[notice.index("How Do I Get A Payment?") :][:2200]
            + "\n[…]\n"
            + notice[notice.index("The Claim Form asks you") :][:1500],
            order[
                order.index("B. Overview of Settlement Terms") : order.index(
                    "B. Overview of Settlement Terms"
                )
                + 1200
            ],
        ]
        evidence = [
            ResearchEvidence(
                url=url,
                publisher="Angeion Group / case administrator"
                if i < 3
                else "U.S. District Court, Southern District of Ohio (administrator-hosted order)",
                source_type="administrator" if i < 3 else "court",
                fetched_at=observed,
                quoted_excerpt=excerpts[i],
                content_sha256=hashlib.sha256(bodies[i]).hexdigest(),
                authoritative_for=["class_definition", "deadline", "proof", "exclusions"]
                if i == 2
                else ["case_identity", "source_links"],
            )
            for i, url in enumerate([HOME, DOCUMENTS, NOTICE, ORDER])
        ]
        return VerifiedSettlement(fetched_at=observed, evidence=evidence)
