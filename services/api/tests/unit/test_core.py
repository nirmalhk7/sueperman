"""Catch unsafe positive matches, parser data loss, and unsupported source claims."""

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError


def core():
    # Lazy imports let missing behavior produce an explicit assertion during RED.
    try:
        from app import schemas
        from app.matching.normalize import normalize_model
        from app.matching.recall import match_recall
        from app.matching.settlement import match_settlement
        from app.providers.receipt import FixtureReceiptExtractor

        return schemas, match_recall, normalize_model, FixtureReceiptExtractor, match_settlement
    except ImportError:
        pytest.fail("Core parser, typed contracts and deterministic matchers are not implemented")


def record():
    return {
        "reference": "26-792",
        "title": "NEWDERY power banks",
        "brand": "NEWDERY",
        "family": "power bank",
        "models": ["ZHX-PB22"],
        "official_url": "https://www.cpsc.gov/Recalls/2026/test",
        "fetched_at": "2026-11-13T17:48:00Z",
        "source_type": "government",
        "publisher": "CPSC",
        "excerpt": "Model ZHX-PB22 is recalled.",
        "remedy_kind": "refund",
        "conditions": [],
    }


@pytest.mark.parametrize(
    "model,want",
    [
        (" zｈx-pb22 ", "verified_match"),
        ("ZHX-PB23", "rejected"),
        ("ZHX-PB22A", "rejected"),
        ("ZHXPB22", "rejected"),
        (None, "needs_review"),
    ],
)
def test_exact_identifier_gate(model, want):
    s, match, normalize, _, _ = core()
    p = s.ProductInput(product_name="Portable Power Bank", brand="NEWDERY", model_number=model)
    result = match(p, s.RecallRecord(**record()))
    assert result.status == want
    assert result.evidence_ids
    assert normalize(" ZHX- PB22A ") == "ZHX-PB22A"


def test_missing_serial_and_false_date_gate():
    s, match, _, _, _ = core()
    r = record()
    r["conditions"] = [{"name": "serial_prefix", "expected": "ABC"}]
    p = s.ProductInput(product_name="Power Bank", brand="NEWDERY", model_number="ZHX-PB22")
    assert match(p, s.RecallRecord(**r)).status == "needs_review"
    p.serial_prefix = "XYZ"
    assert match(p, s.RecallRecord(**r)).status == "rejected"
    r["conditions"] = [{"name": "date_purchased", "expected": ["2023-01-01", "2024-12-31"]}]
    p.date_purchased = date(2025, 1, 1)
    assert match(p, s.RecallRecord(**r)).status == "rejected"


@pytest.mark.parametrize(
    "url",
    [
        "https://www.cpsc.gov.evil.com/a",
        "http://www.cpsc.gov/a",
        "https://www.cpsc.gov@127.0.0.1/a",
        "https://localhost/a",
        "file:///a",
    ],
)
def test_source_mimic_cannot_verify(url):
    s, match, *_ = core()
    r = record() | {"official_url": url}
    p = s.ProductInput(product_name="Power Bank", brand="NEWDERY", model_number="ZHX-PB22")
    assert match(p, s.RecallRecord(**r)).status != "verified_match"


def test_provenance_required_unknown_remedy_stays_unknown():
    s, match, *_ = core()
    with pytest.raises(ValidationError):
        s.RecallRecord(**(record() | {"fetched_at": None}))
    r = s.RecallRecord(**(record() | {"remedy_kind": "unknown"}))
    assert r.remedy_kind == "unknown"
    p = s.ProductInput(product_name="Bottle", brand="Other", model_number="ZHX-PB22")
    assert match(p, r).status == "rejected"


def test_csv_quotes_unicode_duplicates_and_headers():
    *_, parser, _ = core()
    raw = ' ORDER_ID , purchased_at ,merchant, product_name ,brand,model_number,upc\nX,2024-06-12,Store,"Café, bank",NEWDERY,ZHX-PB22,\nX,2024-06-12,Store,"Café, bank",NEWDERY,ZHX-PB22,\n'
    rows = parser().extract(raw.encode())
    assert len(rows) == 1
    assert rows[0].product_name == "Café, bank"
    assert rows[0].date_purchased == date(2024, 6, 12)
    assert rows[0].order_reference_redacted == "***X"
    with pytest.raises(ValueError):
        parser().extract(b'product_name\n""\n')
    with pytest.raises(ValueError):
        parser().extract(b"x" * (10 * 1024 * 1024 + 1))


def test_fixture_has_exact_five_rows_and_real_snapshot():
    s, _, _, parser, _ = core()
    root = Path(__file__).resolve().parents[4]
    rows = parser().extract((root / "demo/orders.csv").read_bytes())
    assert len(rows) == 5
    assert [p.model_number for p in rows] == ["ZHX-PB22", "ZHX-PB23", "DC-BOTTLE-1", None, "DC-EARBUDS-1"]
    recall = s.RecallRecord(**json.loads((root / "demo/recall_fixture.json").read_text()))
    assert recall.reference == "26-792"
    assert recall.safety_instructions
    assert recall.mode == "replay"


def test_settlement_inclusive_dates_expiry_and_missing_date():
    s, _, _, _, match = core()
    rules = s.SettlementRecord(
        title="DEMO SETTLEMENT — Example Earbuds Warranty Class",
        model="DC-EARBUDS-1",
        brand="DemoCo",
        start="2024-01-01",
        end="2025-12-31",
        deadline="2026-12-31",
        source_url="demo/settlement_fixture.json",
        fetched_at="2026-11-13T17:48:00Z",
    )
    p = s.ProductInput(
        product_name="Example Earbuds",
        brand="DemoCo",
        model_number="DC-EARBUDS-1",
        date_purchased="2024-01-01",
    )
    assert match(p, rules, date(2026, 11, 13)).status == "eligible_candidate"
    assert match(p, rules, date(2027, 1, 1)).status == "ineligible"
    p.date_purchased = None
    assert match(p, rules, date(2026, 11, 13)).status == "uncertain"


@pytest.mark.asyncio
async def test_candidates_can_use_product_family_when_brand_missing():
    from app.providers.cpsc import FixtureRecallSource

    s, match, *_ = core()
    p = s.ProductInput(product_name="Portable Power Bank", model_number="ZHX-PB22")
    records = await FixtureRecallSource().search(p)
    assert len(records) == 1
    assert match(p, records[0]).status == "needs_review"


def test_unknown_source_product_identity_requires_review_not_exclusion():
    s, match, *_ = core()
    p = s.ProductInput(product_name="Power Bank", brand="Other", model_number="OTHER-1")
    recall = s.RecallRecord(**(record() | {"brand": "", "family": "", "models": []}))
    assert match(p, recall).status == "needs_review"
