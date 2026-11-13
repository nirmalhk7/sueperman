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


def test_sanitized_exception_keeps_readable_frames_without_receipt_values():
    from app.telemetry import sanitize_event

    event = {
        "event_id": "safe-id",
        "exception": {
            "values": [
                {
                    "type": "RuntimeError",
                    "value": "private receipt",
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "app/main.py",
                                "function": "run_detail",
                                "lineno": 44,
                                "context_line": "return run_view(run)",
                                "vars": {"api_key": "secret-token"},
                            }
                        ]
                    },
                }
            ]
        },
    }
    cleaned = sanitize_event(event, {})
    assert cleaned.get("exception", {}).get("values"), "An actual exception must remain an error event"
    exception = cleaned["exception"]["values"][0]
    assert exception["type"] == "RuntimeError"
    assert exception["value"] == "Application error details redacted"
    assert exception["stacktrace"]["frames"][0]["context_line"] == "return run_view(run)"
    assert "private receipt" not in json.dumps(cleaned)
    assert "secret-token" not in json.dumps(cleaned)


def test_trace_scrubber_removes_query_values_and_raw_attributes():
    try:
        from app.telemetry import sanitize_transaction
    except ImportError:
        pytest.fail("Trace privacy boundary not implemented")
    trace = {
        "type": "transaction",
        "transaction": "/api/products?secret=private-order",
        "contexts": {"trace": {"trace_id": "a" * 32, "span_id": "b" * 16}},
        "request": {"data": "raw receipt"},
        "spans": [
            {
                "op": "http.client",
                "description": "https://api.openai.com/?key=secret-token",
                "data": {"http.request.body": "private receipt"},
                "span_id": "c" * 16,
                "trace_id": "a" * 32,
                "start_timestamp": 1,
                "timestamp": 2,
            }
        ],
    }
    clean = sanitize_transaction(trace, {})
    assert clean["contexts"]["trace"]["trace_id"] == "a" * 32
    assert len(clean["spans"]) == 1
    assert not any(
        s in json.dumps(clean) for s in ["secret-token", "private-order", "private receipt", "raw receipt"]
    )


def test_actual_sdk_sends_sanitized_exception_trace_and_allowed_log(monkeypatch):
    import sentry_sdk
    from sentry_sdk import logger
    from sentry_sdk.transport import HttpTransport

    from app.telemetry import initialize_telemetry

    envelopes = []
    monkeypatch.setattr(HttpTransport, "_send_envelope", lambda self, envelope: envelopes.append(envelope))
    initialize_telemetry("https://public@example.com/1")
    with sentry_sdk.start_transaction(name="private-order", op="test"):
        try:
            raise RuntimeError("private receipt secret-token")
        except RuntimeError:
            sentry_sdk.capture_exception()
        logger.error("Sueperman Sentry verification 1794590000 backend")
    sentry_sdk.flush(timeout=3)
    serialized = "\n".join(e.serialize().decode() for e in envelopes)
    assert "private receipt" not in serialized
    assert "secret-token" not in serialized
    assert "private-order" not in serialized
    assert "Application error details redacted" in serialized
    assert "Sueperman Sentry verification 1794590000 backend" in serialized
    assert "Sueperman request" in serialized
    sentry_sdk.get_client().close()
