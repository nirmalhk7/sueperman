"""Catch live schema drift, unsupported restriction positives, retries and silent fallback."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.matching.recall import match_recall
from app.schemas import ProductInput


def provider(tmp_path, client):
    try:
        from app.providers.cpsc import CPSCRecallSource
    except ImportError:
        pytest.fail("Live CPSC adapter is not implemented")
    return CPSCRecallSource(client=client, cache_dir=tmp_path)


@pytest.mark.asyncio
async def test_real_cpsc_shape_normalizes_description_model_and_remedy(tmp_path):
    raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    async with httpx.AsyncClient() as client:
        with respx.mock as router:
            route = router.get(
                "https://www.saferproducts.gov/RestWebServices/Recall",
                params={"ProductName": "NEWDERY", "format": "json"},
            ).respond(200, json=raw)
            source = provider(tmp_path, client)
            records = await source.search(
                ProductInput(product_name="Portable Power Bank", brand="NEWDERY", model_number="ZHX-PB22")
            )
            assert route.call_count == 1
            assert len(records) == 1
            assert records[0].models == ["ZHX-PB22"]
            assert records[0].reference == "26-792"
            assert records[0].mode == "live"
            assert records[0].fetched_at.utcoffset().total_seconds() == 0
            assert records[0].remedy_kind == "refund"
            assert "Do not throw" in records[0].safety_instructions
            assert records[0].contact_url == "https://www.newdery.com/pages/newdery-power-bank-recalls"
            p = ProductInput(product_name="Portable Power Bank", brand="NEWDERY", model_number="ZHX-PB22")
            assert match_recall(p, records[0]).status == "verified_match"
            p.model_number = "ZHX-PB23"
            assert match_recall(p, records[0]).status == "rejected"
            assert list(tmp_path.glob("*.json"))


@pytest.mark.asyncio
async def test_cpsc_retry_then_schema_failure_is_typed(tmp_path):
    try:
        from app.providers.errors import ProviderUnavailable
    except ImportError:
        pytest.fail("Typed provider failures are not implemented")
    async with httpx.AsyncClient() as client:
        with respx.mock as router:
            route = router.get("https://www.saferproducts.gov/RestWebServices/Recall").mock(
                side_effect=[httpx.Response(503), httpx.Response(200, json={"changed_schema": True})]
            )
            with pytest.raises(ProviderUnavailable):
                await provider(tmp_path, client).search(ProductInput(product_name="bank", brand="NEWDERY"))
            assert route.call_count == 2


@pytest.mark.asyncio
async def test_unsupported_live_restrictions_cannot_produce_positive(tmp_path):
    raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    raw[0]["Description"] += " Only serial numbers ABC100 through ABC200 are affected."
    async with httpx.AsyncClient() as client:
        with respx.mock as router:
            router.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=raw)
            records = await provider(tmp_path, client).search(
                ProductInput(product_name="Power Bank", brand="NEWDERY")
            )
            assert (
                match_recall(
                    ProductInput(product_name="Power Bank", brand="NEWDERY", model_number="ZHX-PB22"),
                    records[0],
                ).status
                == "needs_review"
            )


@pytest.mark.asyncio
async def test_live_candidates_are_deduplicated(tmp_path):
    raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    async with httpx.AsyncClient() as client:
        with respx.mock as r:
            r.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=raw + raw)
            records = await provider(tmp_path, client).search(
                ProductInput(product_name="bank", brand="NEWDERY")
            )
            assert len(records) == 1


@pytest.mark.asyncio
async def test_live_candidate_truncation_is_explicit(tmp_path):
    raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    many = [raw[0] | {"RecallID": 20000 + i, "RecallNumber": f"99{i:03d}"} for i in range(11)]
    async with httpx.AsyncClient() as client:
        with respx.mock as r:
            r.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=many)
            source = provider(tmp_path, client)
            records = await source.search(ProductInput(product_name="bank", brand="NEWDERY"))
            assert len(records) == 10
            assert source.truncated is True
