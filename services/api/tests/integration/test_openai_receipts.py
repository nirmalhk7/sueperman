"""Photo OCR must use OpenAI, preserve review gates, and stop spending at its daily cap."""

import json
from pathlib import Path

import pytest
import respx
from fastapi.testclient import TestClient

PHOTO = Path(__file__).parents[4] / "demo/receipt-synthetic.jpg"


def response(text=None):
    return {
        "status": "completed",
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": text
                        or json.dumps(
                            {
                                "merchant": "Demo Store",
                                "purchased_at": "2024-06-12",
                                "items": [
                                    {
                                        "product_name": "Power Bank",
                                        "brand": "NEWDERY",
                                        "model_number": "ZHX-PB22",
                                        "upc": None,
                                    }
                                ],
                            }
                        ),
                    }
                ],
            }
        ],
    }


def enable(monkeypatch, limit="10"):
    monkeypatch.setenv("OPENAI_RECEIPT_ENABLED", "true")
    monkeypatch.setenv("OPENAI_RECEIPT_DAILY_LIMIT", limit)
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai")
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    monkeypatch.setenv("GEMINI_ENABLED", "false")


def upload(client, data=None):
    return client.post(
        "/api/uploads/purchases", files={"file": ("camera.jpg", data or PHOTO.read_bytes(), "image/jpeg")}
    )


def test_camera_jpeg_uses_openai_and_reuses_import_before_spending(monkeypatch, tmp_path):
    from app.main import create_app

    enable(monkeypatch)
    with respx.mock as routes:
        remote = routes.post("https://api.openai.com/v1/responses").respond(200, json=response())
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/receipt.db")) as client:
            first = upload(client)
            assert first.status_code == 200, first.text
            product = client.get("/api/products").json()[0]["product"]
            assert product["merchant"] == "Demo Store"
            assert product["date_purchased"] == "2024-06-12"
            assert product["model_number"] is None
            assert product["suggested_identifiers"]["model_number"] == "ZHX-PB22"
            assert product["user_confirmed_identifiers"] is False
            assert upload(client).json()["purchase_ids"] == first.json()["purchase_ids"]
            assert remote.call_count == 1
            request = json.loads(remote.calls[0].request.content)
            assert request["store"] is False and request["max_output_tokens"] == 1024
            assert "tools" not in request
            assert request["input"][0]["content"][1]["type"] == "input_image"
            assert request["input"][0]["content"][1]["image_url"].startswith("data:image/jpeg;base64,")


def test_daily_photo_budget_survives_restart_and_stops_before_remote_request(monkeypatch, tmp_path):
    from app.main import create_app

    enable(monkeypatch, "1")
    url = f"sqlite:///{tmp_path}/budget.db"
    with respx.mock as routes:
        remote = routes.post("https://api.openai.com/v1/responses").respond(200, json=response())
        with TestClient(create_app(database_url=url)) as client:
            assert upload(client).status_code == 200
        with TestClient(create_app(database_url=url)) as client:
            assert upload(client).status_code == 200  # cached import does not consume budget
            blocked = upload(client, PHOTO.read_bytes() + b"second capture")
            assert blocked.status_code == 429
            assert remote.call_count == 1


@pytest.mark.parametrize(
    "body",
    [
        {"status": "incomplete", "output": []},
        {
            "status": "completed",
            "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "Cannot read"}]}],
        },
        response('{"items":[]}'),
        response('{"purchased_at":"not-a-date","items":[{"product_name":"Bank"}]}'),
    ],
)
def test_unreadable_or_invalid_ocr_never_imports_guessed_products(monkeypatch, tmp_path, body):
    from app.main import create_app

    enable(monkeypatch)
    with respx.mock as routes:
        remote = routes.post("https://api.openai.com/v1/responses").respond(200, json=body)
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/invalid.db")) as client:
            assert upload(client).status_code == 503
            assert client.get("/api/products").json() == []
            assert remote.call_count == 1


def test_daily_budget_is_atomic_under_concurrent_upload_reservations(tmp_path):
    from concurrent.futures import ThreadPoolExecutor

    from app.db import database
    from app.providers.openai_receipt import reserve_receipt_call

    engine, factory = database(f"sqlite:///{tmp_path}/concurrent.db")
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            accepted = list(pool.map(lambda _: reserve_receipt_call(factory, 3), range(12)))
        assert sum(accepted) == 3
        assert reserve_receipt_call(factory, 3) is False
    finally:
        engine.dispose()


def test_ocr_failure_logs_only_safe_error_classification(monkeypatch, tmp_path, caplog):
    from app.main import create_app

    enable(monkeypatch)
    with respx.mock as routes:
        routes.post("https://api.openai.com/v1/responses").respond(400, json={"error": {
            "code": "invalid_json_schema", "message": "private receipt and test-openai", "param": "text.format.schema"
        }})
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/logs.db")) as client:
            with caplog.at_level("WARNING"):
                assert upload(client).status_code == 503
            assert "error_type=HTTPStatusError" in caplog.text
            assert "status=400" in caplog.text
            assert "code=invalid_json_schema" in caplog.text
            assert "private receipt" not in caplog.text
            assert "test-openai" not in caplog.text
