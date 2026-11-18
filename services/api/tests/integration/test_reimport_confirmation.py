"""Deleted file retries must require current consent before extraction or insertion."""

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app import deletion
from app.db import database
from app.models import Purchase

CSV = b"order_id,purchased_at,merchant,product_name,brand,model_number\nREIMPORT,2024-06-12,Shop,Power Bank,NEWDERY,ZHX-PB22\n"


def file_fingerprint(kind, content):
    return hashlib.sha256(f"{kind}:{hashlib.sha256(content).hexdigest()}".encode()).hexdigest()


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("GEMINI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    url = f"sqlite:///{tmp_path / 'imports.db'}"
    app = create_app(url)
    with TestClient(app) as client:
        engine, factory = database(url)
        runtime = app.state.deletion_runtime
        journal, lineage = runtime.path, runtime.lineage
        try:
            yield client, journal, lineage, factory
        finally:
            engine.dispose()


def request(client, content=CSV, *, token=None, kind="csv"):
    names = {"csv": ("purchases.csv", "text/csv"), "image": ("receipt.png", "image/png")}
    name, mime = names[kind]
    return client.post("/api/uploads/purchases", files={"file": (name, content, mime)},
                       data={"reimport_confirmation": token} if token else {})


def erase_import(workspace, identifiers, content=CSV, kind="csv"):
    _client, journal, lineage, factory = workspace
    for identifier in identifiers:
        deletion.record_deletion(journal, identifier, import_fingerprint=file_fingerprint(kind, content),
                                 expected_lineage=lineage)
        with factory.begin() as session:
            deletion.purge_purchase(session, identifier)


def test_deleted_csv_requires_current_confirmation_and_new_deletion_invalidates_old_token(workspace):
    client, journal, lineage, factory = workspace
    first = request(client).raise_for_status().json()
    erase_import(workspace, first["purchase_ids"])
    denied = request(client)
    assert denied.status_code == 409
    token = denied.json()["reimport_token"]
    assert denied.json()["code"] == "REIMPORT_CONFIRMATION_REQUIRED"
    with factory() as session:
        assert session.scalar(select(Purchase)) is None
    confirmed = request(client, token=token)
    assert confirmed.status_code == 200
    assert confirmed.json()["purchase_ids"] != first["purchase_ids"]
    erase_import(workspace, confirmed.json()["purchase_ids"])
    stale = request(client, token=token)
    assert stale.status_code == 409
    assert stale.json()["reimport_token"] != token
    current = request(client, token=stale.json()["reimport_token"])
    assert current.status_code == 200
    assert deletion.reimport_challenge(journal, file_fingerprint("csv", CSV), expected_lineage=lineage)


def test_deleted_receipt_is_blocked_before_model_configuration_or_quota(workspace, monkeypatch):
    from app.providers.gemini import GeminiReceiptExtractor

    async def forbidden(*_args):
        raise AssertionError("Receipt extraction happened before re-import consent")

    monkeypatch.setattr(GeminiReceiptExtractor, "extract", forbidden)
    client, journal, lineage, _factory = workspace
    content = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
    deletion.record_deletion(journal, str(uuid4()), import_fingerprint=file_fingerprint("image", content),
                             expected_lineage=lineage)
    response = request(client, content, kind="image")
    assert response.status_code == 409
    assert response.json()["reimport_token"]


def test_deletion_during_extraction_prevents_delayed_recreation(workspace, monkeypatch):
    from app.providers.gemini import GeminiReceiptExtractor
    from app.schemas import ProductInput

    client, journal, lineage, factory = workspace
    content = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
    async def extracting(_self, _content, _mime):
        deletion.record_deletion(journal, str(uuid4()), import_fingerprint=file_fingerprint("image", content),
                                 expected_lineage=lineage)
        return [ProductInput(product_name="Power Bank")]

    monkeypatch.setattr(GeminiReceiptExtractor, "extract", extracting)
    response = request(client, content, kind="image")
    assert response.status_code == 409
    with factory() as session:
        assert session.scalar(select(Purchase)) is None


def test_confirmed_partial_receipt_reimport_restores_missing_item_instead_of_reusing_survivors(workspace, monkeypatch):
    from app.providers.gemini import GeminiReceiptExtractor
    from app.schemas import ProductInput

    client, _journal, _lineage, factory = workspace
    content = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()

    async def extracting(_self, _content, _mime):
        return [ProductInput(product_name="First item"), ProductInput(product_name="Second item")]

    monkeypatch.setattr(GeminiReceiptExtractor, "extract", extracting)
    first = request(client, content, kind="image").raise_for_status().json()
    erase_import(workspace, first["purchase_ids"][:1], content=content, kind="image")
    denied = request(client, content, kind="image")
    assert denied.status_code == 409
    restored = request(client, content, kind="image", token=denied.json()["reimport_token"])
    assert restored.status_code == 200
    assert len(restored.json()["purchase_ids"]) == 2
    assert first["purchase_ids"][0] not in restored.json()["purchase_ids"]
    assert first["purchase_ids"][1] in restored.json()["purchase_ids"]
    with factory() as session:
        assert len(session.scalars(select(Purchase)).all()) == 2


def test_confirmation_that_becomes_stale_during_extraction_cannot_restore_purchase(workspace, monkeypatch):
    from app.providers.gemini import GeminiReceiptExtractor
    from app.schemas import ProductInput

    client, journal, lineage, factory = workspace
    content = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
    fingerprint = file_fingerprint("image", content)
    deletion.record_deletion(journal, str(uuid4()), import_fingerprint=fingerprint, expected_lineage=lineage)
    token = request(client, content, kind="image").json()["reimport_token"]

    async def extracting(_self, _content, _mime):
        deletion.record_deletion(journal, str(uuid4()), import_fingerprint=fingerprint, expected_lineage=lineage)
        return [ProductInput(product_name="Power Bank")]

    monkeypatch.setattr(GeminiReceiptExtractor, "extract", extracting)
    stale = request(client, content, kind="image", token=token)
    assert stale.status_code == 409
    assert stale.json()["reimport_token"] != token
    with factory() as session:
        assert session.scalar(select(Purchase)) is None


def test_missing_bound_journal_stops_import_instead_of_assuming_empty_deletion_history(workspace):
    client, journal, _lineage, factory = workspace
    journal.unlink()
    response = request(client)
    assert response.status_code == 503
    assert response.json()["code"] == "DELETION_HISTORY_UNAVAILABLE"
    with factory() as session:
        assert session.scalar(select(Purchase)) is None


def test_reordered_partial_receipt_restores_deleted_item_and_preserves_corrected_survivor(workspace, monkeypatch):
    """OCR row order cannot replace missing first item with a duplicate survivor."""
    from app.providers.gemini import GeminiReceiptExtractor
    from app.schemas import ProductInput

    client, _journal, _lineage, _factory = workspace
    content = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
    rows = [ProductInput(product_name="First item", merchant="First shop"),
            ProductInput(product_name="Second item", merchant="Second shop")]

    async def extracting(_self, _content, _mime):
        return list(rows)

    monkeypatch.setattr(GeminiReceiptExtractor, "extract", extracting)
    first = request(client, content, kind="image").raise_for_status().json()
    corrected = client.post(f"/api/products/{first['product_ids'][1]}/corrections", json={
        "confirmed": True, "model_number": "USER-VERIFIED", "brand": "Reviewed brand"})
    corrected.raise_for_status()
    client.post(f"/api/purchases/{first['purchase_ids'][0]}/delete", json={"confirmed": True}).raise_for_status()
    rows.reverse()
    denied = request(client, content, kind="image")
    assert denied.status_code == 409
    restored = request(client, content, kind="image", token=denied.json()["reimport_token"])
    assert restored.status_code == 200
    products = client.get("/api/products").json()
    assert sorted(row["product"]["product_name"] for row in products) == ["First item", "Second item"]
    survivor = next(row for row in products if row["purchase_id"] == first["purchase_ids"][1])
    assert survivor["id"] == corrected.json()["id"]
    assert survivor["product"]["model_number"] == "USER-VERIFIED"
    assert survivor["product"]["brand"] == "Reviewed brand"
    assert set(restored.json()["product_ids"]) == {row["id"] for row in products}


@pytest.mark.parametrize("replacement", ["missing", "changed", "legacy", "ambiguous"])
def test_partial_receipt_uncertain_alignment_refuses_without_changing_survivor(workspace, monkeypatch, replacement):
    """Changed/missing OCR facts or absent provenance must not silently lose an item."""
    from app.providers.gemini import GeminiReceiptExtractor
    from app.schemas import ProductInput

    client, _journal, _lineage, factory = workspace
    content = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
    rows = [ProductInput(product_name="First item"), ProductInput(product_name="Second item")]
    if replacement == "ambiguous":
        rows = [ProductInput(product_name="Same item"), ProductInput(product_name="Same item")]

    async def extracting(_self, _content, _mime):
        return list(rows)

    monkeypatch.setattr(GeminiReceiptExtractor, "extract", extracting)
    imported = request(client, content, kind="image").raise_for_status().json()
    client.post(f"/api/purchases/{imported['purchase_ids'][0]}/delete", json={"confirmed": True}).raise_for_status()
    before = client.get("/api/products").json()
    if replacement == "missing":
        rows[:] = rows[1:]
    elif replacement == "changed":
        rows[1] = ProductInput(product_name="Different surviving item")
    elif replacement == "legacy":
        with factory.begin() as session:
            remaining = session.get(Purchase, imported["purchase_ids"][1])
            remaining.payload = {key: value for key, value in remaining.payload.items()
                                 if key not in {"import_facts", "import_count"}}
    denied = request(client, content, kind="image")
    assert denied.status_code == 409
    response = request(client, content, kind="image", token=denied.json()["reimport_token"])
    assert response.status_code == 409
    assert "CSV" in response.json()["message"]
    assert client.get("/api/products").json() == before
