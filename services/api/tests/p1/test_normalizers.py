"""New source-specific support must not turn changed/nearby products into positives."""

import copy
import json
from pathlib import Path

import httpx
import pytest

from app.matching.recall import match_recall
from app.providers.cpsc import CPSCRecallSource
from app.schemas import ProductInput

FIXTURES = Path(__file__).parents[1] / "fixtures/p1-recalls"


def captured(number):
    return json.loads((FIXTURES / f"{number}.json").read_text())


async def fetch(tmp_path, row, *, enabled=True):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[row]))) as client:
        try:
            source = CPSCRecallSource(client=client, cache_dir=tmp_path, reviewed_notices=enabled)
        except TypeError:
            pytest.fail("Opt-in reviewed recall normalizers are missing")
        return (await source.search(ProductInput(product_name="Power bank", brand="test")))[0]


@pytest.mark.asyncio
@pytest.mark.parametrize("number,brand,model", [("26610", "Flaunt", "E33A"),
                                               ("25390", "iStore", "IST-09991/W05")])
async def test_additional_notices_exact_near_missing_and_brand_guards(tmp_path, number, brand, model):
    record = await fetch(tmp_path, captured(number))
    assert record.reference == number[:2] + "-" + number[2:]
    assert record.models == [model]
    assert record.remedy_kind == "refund"
    assert record.official_url == captured(number)["URL"]
    assert "photograph" in record.instructions.casefold()
    assert record.required_documents
    for candidate, wanted in [(model, "verified_match"), (model + "X", "rejected"),
                              (model.replace("/", "").replace("-", "") if "/" in model else "E33-A", "rejected"),
                              (None, "needs_review")]:
        product = ProductInput(product_name="Magnetic power bank", brand=brand, model_number=candidate)
        assert match_recall(product, record).status == wanted
    assert match_recall(ProductInput(product_name="Power bank", brand="Other", model_number=model), record).status == "rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["Description", "Title", "Remedies", "ConsumerContact"])
async def test_changed_official_fields_cannot_reuse_reviewed_normalizer(tmp_path, field):
    row = copy.deepcopy(captured("26610"))
    row[field] = ([{"Name": "Only serial ABC100 is included."}] if field == "Remedies"
                  else row[field] + " Only serial ABC100 is included.")
    record = await fetch(tmp_path, row)
    assert match_recall(ProductInput(product_name="Power bank", brand="Flaunt", model_number="E33A"), record).status == "needs_review"
    assert record.conditions[0].name == "unsupported_source_conditions"


@pytest.mark.asyncio
async def test_additional_support_is_opt_in_and_no_required_receipt_is_invented(tmp_path):
    row = captured("25390")
    disabled = await fetch(tmp_path, row, enabled=False)
    assert disabled.models == []
    enabled = await fetch(tmp_path, row)
    assert not any("receipt" in item.casefold() for item in enabled.required_documents)
    assert "not be required" in enabled.instructions


@pytest.mark.asyncio
async def test_conflicting_duplicate_notice_cannot_hide_changed_restriction(tmp_path):
    from app.providers.errors import ProviderUnavailable
    row = captured("26610")
    conflicting = row | {"Description": row["Description"] + " Only serial ABC100 is included."}
    async with httpx.AsyncClient(transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json=[row, conflicting]))) as client:
        source = CPSCRecallSource(client=client, cache_dir=tmp_path, reviewed_notices=True)
        with pytest.raises(ProviderUnavailable):
            await source.search(ProductInput(product_name="Power bank", brand="Flaunt"))


@pytest.mark.asyncio
async def test_official_flaunt_battery_charger_name_is_supported_without_relaxing_model(tmp_path):
    record = await fetch(tmp_path, captured("26610"))
    product = ProductInput(product_name="Flaunt MagSafe Battery Charger", brand="Flaunt", model_number="E33A")
    result = match_recall(product, record)
    assert result.status == "verified_match"
    assert next(c for c in result.conditions if c.name == "product_family").expected == ["power bank", "battery charger"]
    product.model_number = "E33AX"
    assert match_recall(product, record).status == "rejected"
