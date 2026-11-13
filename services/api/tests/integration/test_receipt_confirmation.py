"""Catch model identifiers promoted without review, missing confirmation, and stale matches."""

import json
from pathlib import Path

import pytest
import respx
from fastapi.testclient import TestClient


@pytest.mark.parametrize("extension,mime", [("png", "image/png"), ("pdf", "application/pdf")])
def test_confirmed_scan_can_match_and_later_identifier_edits_are_blocked(
    tmp_path, monkeypatch, extension, mime
):
    from app.main import create_app

    monkeypatch.setenv("GEMINI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    output = json.dumps(
        {
            "merchant": "Demo Store",
            "purchased_at": "2024-06-12",
            "items": [{"product_name": "Power Bank", "brand": "NEWDERY", "model_number": "ZHX-PB22"}],
        }
    )
    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).respond(
            200,
            json={
                "candidates": [
                    {"content": {"role": "model", "parts": [{"text": output}]}, "finishReason": "STOP"}
                ]
            },
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/scan.db")) as client:
            content = (Path(__file__).parents[4] / f"demo/receipt-synthetic.{extension}").read_bytes()
            uploaded = client.post(
                "/api/uploads/purchases", files={"file": (f"receipt.{extension}", content, mime)}
            ).json()
            pid = uploaded["product_ids"][0]
            endpoint = f"/api/products/{pid}/confirm-identifiers"
            assert (
                client.post(endpoint, json={"confirmed": False, "model_number": "ZHX-PB22"}).status_code
                == 422
            )
            confirmed = client.post(
                endpoint, json={"confirmed": True, "brand": "NEWDERY", "model_number": "ZHX-PB22"}
            )
            assert confirmed.status_code == 200
            assert confirmed.json()["product"]["user_confirmed_identifiers"] is True
            assert confirmed.json()["product"]["model_number"] == "ZHX-PB22"
            run = client.post(
                "/api/runs",
                json={
                    "purchase_ids": uploaded["purchase_ids"],
                    "mode": "demo",
                    "idempotency_key": "reviewed-scan",
                },
            ).json()
            result = client.get(f"/api/runs/{run['run_id']}").json()
            assert result["summary"]["verified_matches"] == 1
            assert (
                client.post(endpoint, json={"confirmed": True, "model_number": "ZHX-PB23"}).status_code == 409
            )


def test_duplicate_scan_returns_existing_import_without_spending_again(tmp_path, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("GEMINI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    with respx.mock as routes:
        remote = routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).respond(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": '{"items":[{"product_name":"Power Bank"}]}'}],
                        },
                        "finishReason": "STOP",
                    }
                ]
            },
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/cache.db")) as client:
            data = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
            a = client.post("/api/uploads/purchases", files={"file": ("receipt.png", data, "image/png")})
            b = client.post("/api/uploads/purchases", files={"file": ("receipt.png", data, "image/png")})
            assert a.status_code == b.status_code == 200
            assert a.json()["purchase_ids"] == b.json()["purchase_ids"]
            assert remote.call_count == 1


def test_confirmation_does_not_promote_an_unreviewed_extracted_brand(tmp_path, monkeypatch):
    from app.main import create_app

    monkeypatch.setenv("GEMINI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).respond(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [
                                {
                                    "text": '{"items":[{"product_name":"Power Bank","brand":"NEWDERY","model_number":"ZHX-PB22"}]}'
                                }
                            ],
                        },
                        "finishReason": "STOP",
                    }
                ]
            },
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/brand.db")) as client:
            data = (Path(__file__).parents[4] / "demo/receipt-synthetic.png").read_bytes()
            uploaded = client.post(
                "/api/uploads/purchases", files={"file": ("receipt.png", data, "image/png")}
            ).json()
            response = client.post(
                f"/api/products/{uploaded['product_ids'][0]}/confirm-identifiers",
                json={"confirmed": True, "model_number": "ZHX-PB22"},
            )
            assert response.status_code == 200
            assert response.json()["product"]["brand"] is None
