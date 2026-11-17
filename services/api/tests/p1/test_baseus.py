"""Baseus replacement units and missing serials must never receive positive drafts."""
import copy
import json
from pathlib import Path

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.matching.recall import match_recall
from app.providers.cpsc import CPSCRecallSource
from app.providers.receipt import FixtureReceiptExtractor
from app.schemas import Condition, ProductInput

ROW = json.loads((Path(__file__).parents[1] / "fixtures/p1-recalls/25248.json").read_text())


@pytest.mark.asyncio
async def test_exact_serial_restriction_and_model_punctuation(tmp_path):
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=[ROW]))) as client:
        source = CPSCRecallSource(client=client, cache_dir=tmp_path, reviewed_notices=True)
        record = (await source.search(ProductInput(product_name="Portable charger", brand="Baseus")))[0]
    assert record.remedy_kind == "replacement"
    assert record.models == ["BS-30KP365"]
    assert "Do not throw" in record.safety_instructions
    for model, serial, expected in [
        ("BS-30KP365", "SN123D", "verified_match"),
        *[("BS-30KP365", f"SN123{digit}", "verified_match") for digit in "0123456789"],
        ("BS-30KP365", "SN123A", "rejected"),
        ("BS-30KP365", "D", "rejected"),
        ("BS-30KP365", "otherD", "rejected"),
        ("BS-30KP365", "SN123d", "rejected"),
        ("BS-30KP365", None, "needs_review"),
        ("BS-30KP365", "", "needs_review"),
        ("BS30KP365", "SN123D", "rejected"),
        ("BS 30KP365", "SN123D", "rejected"),
        ("BS-30KP365X", "SN123D", "rejected"),
        (None, "SN123D", "needs_review"),
    ]:
        product = ProductInput(product_name="Baseus portable charger", brand="Baseus",
                               model_number=model, serial_number=serial)
        assert match_recall(product, record).status == expected
    record.conditions.append(Condition(name="unknown_restriction", expected="review"))
    product = ProductInput(product_name="Portable charger", brand="Baseus",
                           model_number="BS-30KP365", serial_number="SN123D")
    assert match_recall(product, record).status == "needs_review"


def test_csv_preserves_complete_serial_without_overloading_prefix():
    product = FixtureReceiptExtractor().extract(
        b"product_name,brand,model_number,serial_number\nPortable charger,Baseus,BS-30KP365,SN123D\n"
    )[0]
    assert product.serial_number == "SN123D"
    assert product.serial_prefix is None


@pytest.mark.parametrize("changed", [False, True])
def test_baseus_import_evidence_and_local_export(tmp_path, monkeypatch, changed):
    monkeypatch.setenv("P1_ENABLED", "true")
    monkeypatch.setenv("P1_MONITOR_ENABLED", "true")
    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")
    from app.main import create_app
    row = copy.deepcopy(ROW)
    if changed:
        row["Description"] += " Only batch X is affected."
    with respx.mock as remote, TestClient(create_app(f"sqlite:///{tmp_path}/test.db")) as c:
        remote.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=[row])
        uploaded = c.post("/api/uploads/purchases", files={"file": ("baseus.csv",
            b"product_name,brand,model_number,serial_number\nPortable charger,Baseus,BS-30KP365,SN123D\n", "text/csv")}).json()
        run = c.post("/api/runs", json={"purchase_ids": uploaded["purchase_ids"], "mode": "live",
                                      "idempotency_key": "baseus"}).json()
        opportunities = c.get("/api/opportunities", params={"run_id": run["run_id"]}).json()
        assert len(opportunities) == 1
        detail = c.get("/api/opportunities/" + opportunities[0]["id"]).json()
        assert detail["status"] == ("needs_review" if changed else "verified_match")
        assert detail["evidence"][0]["url"] == ROW["URL"]
        assert detail["evidence"][0]["fetched_at"]
        assert len(detail["evidence"][0]["content_sha256"]) == 64
        prepared = c.post(f"/api/opportunities/{detail['id']}/claim-packet")
        if changed:
            assert prepared.status_code == 409
        else:
            watch = c.post(f"/api/opportunities/{detail['id']}/source-monitor", json={"enabled": True})
            assert watch.status_code == 200
            path = "/api/claim-packets/" + prepared.json()["id"]
            assert c.post(path + "/export").status_code == 409
            assert c.post(path + "/approve-local", json={"confirmed": True}).status_code == 200
            exported = c.post(path + "/export")
            assert exported.status_code == 200
            assert ROW["URL"] in exported.text
            assert "not an external submission" in exported.text


@pytest.mark.asyncio
async def test_baseus_public_watch_uses_registered_brand_and_revokes_changed_source(tmp_path):
    from app.p1.monitoring import fetch_public
    from app.providers.errors import ProviderUnavailable
    with respx.mock as remote:
        route = remote.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=[ROW])
        record = await fetch_public("25-248")
        assert record.models == ["BS-30KP365"]
        changed = ROW | {"Description": ROW["Description"] + " Only batch X is affected."}
        route.respond(200, json=[ROW, changed])
        with pytest.raises(ProviderUnavailable):
            await fetch_public("25-248")


def test_changed_baseus_source_revokes_existing_export(tmp_path, monkeypatch):
    monkeypatch.setenv("P1_ENABLED", "true")
    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")
    from app.main import create_app
    with respx.mock as remote, TestClient(create_app(f"sqlite:///{tmp_path}/test.db")) as c:
        route = remote.get("https://www.saferproducts.gov/RestWebServices/Recall").respond(200, json=[ROW])
        uploaded = c.post("/api/uploads/purchases", files={"file": ("baseus.csv",
            b"product_name,brand,model_number,serial_number\nPortable charger,Baseus,BS-30KP365,SN123D\n", "text/csv")}).json()
        def run(key):
            return c.post("/api/runs", json={"purchase_ids": uploaded["purchase_ids"],
                                            "mode": "live", "idempotency_key": key}).json()
        first = run("first")
        item = c.get("/api/opportunities", params={"run_id": first["run_id"]}).json()[0]
        path = "/api/claim-packets/" + c.post(f"/api/opportunities/{item['id']}/claim-packet").json()["id"]
        assert c.post(path + "/approve-local", json={"confirmed": True}).status_code == 200
        route.respond(200, json=[ROW | {"Description": ROW["Description"] + " Only batch X is affected."}])
        run("changed")
        assert c.post(path + "/export").status_code == 409
