import json

import pytest


def test_sentry_event_drops_receipts_tokens_requests_and_raw_errors():
    try:
        from app.telemetry import sanitize_event
    except ImportError:
        pytest.fail("Sanitized telemetry boundary not implemented")
    event = {
        "event_id": "abc",
        "level": "error",
        "message": "receipt private-order and secret-token",
        "exception": {"values": [{"value": "secret-token"}]},
        "request": {"data": "full receipt"},
        "user": {"email": "person@example.test"},
        "breadcrumbs": [{"message": "raw document"}],
        "extra": {"api_key": "secret-token"},
        "tags": {
            "run_id": "b51cb33a-c09f-432b-891a-2d594ac58c64",
            "provider": "cpsc",
            "private": "secret-token",
        },
    }
    cleaned = sanitize_event(event, {})
    raw = json.dumps(cleaned)
    for value in [
        "secret-token",
        "private-order",
        "full receipt",
        "person@example.test",
        "raw document",
        "api_key",
    ]:
        assert value not in raw
    assert cleaned["tags"] == {"run_id": "b51cb33a-c09f-432b-891a-2d594ac58c64", "provider": "cpsc"}
