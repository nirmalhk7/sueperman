"""Catch unbounded receipt generation and SDK retries that spend extra credits."""

import json

import httpx
import pytest
import respx

from app.providers.gemini import GeminiReceiptExtractor


@pytest.mark.asyncio
async def test_receipt_request_has_bounded_output():
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
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

    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).mock(side_effect=respond)
        products = await GeminiReceiptExtractor("test").extract(b"%PDF-1.4\nsynthetic", "application/pdf")
    assert products[0].product_name == "Power Bank"
    assert sent[0]["generationConfig"]["maxOutputTokens"] == 1024


@pytest.mark.asyncio
async def test_receipt_uses_json_schema_field_accepted_by_gemini_rest():
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
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

    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).mock(side_effect=respond)
        await GeminiReceiptExtractor("test").extract(b"%PDF-1.4\nsynthetic", "application/pdf")
    config = sent[0]["generationConfig"]
    assert "responseSchema" not in config
    schema = config["responseJsonSchema"]
    assert schema["properties"]["items"]["items"]["required"] == ["product_name"]
    assert set(schema["properties"]["items"]["items"]["properties"]) == {
        "product_name",
        "brand",
        "model_number",
        "upc",
    }


@pytest.mark.asyncio
async def test_gemini_deadline_meets_provider_minimum():
    timeouts = []

    def respond(request):
        timeouts.append(request.extensions["timeout"]["read"])
        return httpx.Response(
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

    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).mock(side_effect=respond)
        await GeminiReceiptExtractor("test").extract(b"%PDF-1.4\nsynthetic", "application/pdf")
    assert timeouts[0] >= 10


@pytest.mark.asyncio
async def test_current_flash_lite_keeps_sampling_defaults_and_minimal_thinking():
    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
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

    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent"
        ).mock(side_effect=respond)
        await GeminiReceiptExtractor("test", "gemini-3.5-flash-lite").extract(
            b"%PDF-1.4\nsynthetic", "application/pdf"
        )
    config = sent[0]["generationConfig"]
    assert "temperature" not in config
    assert config["thinkingConfig"]["thinking_level"] == "MINIMAL"


@pytest.mark.asyncio
async def test_wire_schema_uses_supported_constraints_but_local_validation_stays_strict():
    import pytest

    from app.providers.gemini import validate_receipt

    sent = []

    def respond(request):
        sent.append(json.loads(request.content))
        return httpx.Response(
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

    with respx.mock as routes:
        routes.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).mock(side_effect=respond)
        await GeminiReceiptExtractor("test").extract(b"%PDF-1.4\nsynthetic", "application/pdf")
    schema = sent[0]["generationConfig"]["responseJsonSchema"]

    def check(value):
        if isinstance(value, dict):
            assert not {"format", "default", "minLength", "maxLength"} & value.keys()
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(schema)
    for raw in [
        '{"purchased_at":"bad-date","items":[{"product_name":"Test"}]}',
        json.dumps({"items": [{"product_name": "x" * 501}]}),
        '{"items":[{"product_name":"Test","invented":"yes"}]}',
    ]:
        with pytest.raises(ValueError):
            validate_receipt(raw)
