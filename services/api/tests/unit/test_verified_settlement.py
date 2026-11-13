"""Catch unverified authorities, changed terms, missing facts and unsafe packet assertions."""

from datetime import date
from pathlib import Path

import httpx
import pytest

from app.schemas import ProductInput

FIXTURES = Path(__file__).parents[1] / "fixtures/settlement"


def source():
    from app.providers.settlement import VerifiedSettlementSource

    return VerifiedSettlementSource


def transport(changed=False, redirect=False):
    def reply(request):
        path = request.url.path
        if redirect:
            return httpx.Response(302, headers={"location": "https://127.0.0.1/private"})
        if path == "/":
            content = (FIXTURES / "home.html").read_bytes()
        elif path == "/important-documents":
            content = (FIXTURES / "documents.html").read_bytes()
        elif "Notice" in path:
            content = (FIXTURES / "notice.pdf").read_bytes()
        else:
            content = (FIXTURES / "order.pdf").read_bytes()
        if changed and path == "/":
            content = content.replace(b"December 21, 2026", b"December 21, 2025")
        return httpx.Response(200, content=content)

    return httpx.MockTransport(reply)


@pytest.mark.asyncio
async def test_cross_verified_sources_make_live_preparation_only_case():
    async with httpx.AsyncClient(transport=transport()) as client:
        record = await source()(client=client).verify()
    assert record.case_number == "2:21-cv-00022"
    assert record.deadline == date(2026, 12, 21)
    assert record.start == date(2018, 12, 9)
    assert record.end == date(2026, 8, 23)
    assert record.simulated is False
    assert {e.source_type for e in record.evidence} == {"administrator", "court"}
    assert all(e.content_sha256 and e.fetched_at for e in record.evidence)


@pytest.mark.asyncio
@pytest.mark.parametrize("changed,redirect", [(True, False), (False, True)])
async def test_changed_deadline_or_redirect_fails_closed(changed, redirect):
    from app.providers.errors import ProviderUnavailable

    async with httpx.AsyncClient(transport=transport(changed, redirect)) as client:
        with pytest.raises(ProviderUnavailable):
            await source()(client=client).verify()


@pytest.mark.asyncio
async def test_settlement_unknown_facts_stay_uncertain_and_packet_does_not_attest():
    from app.claims.compose import compose_settlement
    from app.matching.settlement import match_verified_settlement

    async with httpx.AsyncClient(transport=transport()) as client:
        record = await source()(client=client).verify()
    product = ProductInput(
        product_name="Prescription drug", merchant="Kroger", date_purchased=date(2024, 6, 12)
    )
    result = match_verified_settlement(product, record, date(2026, 11, 13))
    assert result.status == "uncertain"
    assert {"insured_payment", "us_or_territories", "class_exclusions", "proof_requirements"} <= {
        c.name for c in result.conditions if c.status == "unknown"
    }
    packet = compose_settlement(product, record, result)
    assert packet["mode"] == "live"
    assert packet["status"] == "ready_for_review"
    assert packet["user_declaration_required"] is True
    assert "not an external submission" in packet["markdown"]
    assert "I certify" not in packet["markdown"]
    assert "I paid" not in packet["markdown"]
    assert "December 21, 2026" in packet["markdown"]
    assert record.official_url in packet["markdown"]
    assert match_verified_settlement(product, record, date(2026, 12, 22)).status == "expired"
    assert (
        match_verified_settlement(
            product.model_copy(update={"merchant": "Other"}), record, date(2026, 11, 13)
        ).status
        == "ineligible"
    )
    assert (
        match_verified_settlement(
            product.model_copy(update={"date_purchased": date(2018, 12, 8)}), record, date(2026, 11, 13)
        ).status
        == "ineligible"
    )


def test_expired_or_unverified_settlement_cannot_be_approved_or_exported():
    from types import SimpleNamespace

    from app.api.claims import draft_allowed

    current = {
        "status": "uncertain",
        "simulated": False,
        "preparation_only": True,
        "sources_verified": True,
        "deadline_at": "2099-12-31",
    }
    assert draft_allowed(SimpleNamespace(kind="settlement", payload=current))
    for update in [
        {"deadline_at": "2020-01-01"},
        {"sources_verified": False},
        {"simulated": True},
        {"status": "ineligible"},
        {"preparation_only": False},
    ]:
        assert not draft_allowed(SimpleNamespace(kind="settlement", payload=current | update))


@pytest.mark.asyncio
async def test_unreviewed_primary_document_revision_fails_closed():
    from app.providers.errors import ProviderUnavailable
    from app.providers.settlement import NOTICE

    original = transport()

    async def revised(request):
        response = await original.handle_async_request(request)
        if str(request.url) == NOTICE:
            return httpx.Response(200, content=response.content + b"\n% Unreviewed document revision\n")
        return response

    async with httpx.AsyncClient(transport=httpx.MockTransport(revised)) as client:
        with pytest.raises(ProviderUnavailable):
            await source()(client=client).verify()


@pytest.mark.asyncio
async def test_notice_excerpt_includes_actual_deadline_and_proof_passages():
    async with httpx.AsyncClient(transport=transport()) as client:
        record = await source()(client=client).verify()
    notice = record.evidence[2].quoted_excerpt
    assert "DECEMBER 21, 2026" in notice
    assert "$8,000" in notice
    assert "Unknown Claimant" in notice
