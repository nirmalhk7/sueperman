"""Operational telemetry only: no receipt facts, request data, credentials or model content."""

import re
from uuid import UUID

VERIFICATION = re.compile(r"^Sueperman Sentry verification [0-9]{10,16} (?:backend|frontend)$")
SAFE_TRACE = {"trace_id", "span_id", "parent_span_id", "op", "status", "origin"}
SAFE_FRAME = {
    "filename",
    "function",
    "module",
    "lineno",
    "colno",
    "in_app",
    "context_line",
    "pre_context",
    "post_context",
}


def safe_message(value):
    return (
        value
        if isinstance(value, str) and VERIFICATION.fullmatch(value)
        else "Application error details redacted"
    )


def scrub_source(line):
    # Preserve source structure and locations without copying string literals.
    return re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", '"<redacted>"', str(line))


def common(event):
    result = {
        k: event[k]
        for k in ["event_id", "timestamp", "platform", "environment", "release", "sdk", "level"]
        if k in event
    }
    trace = event.get("contexts", {}).get("trace")
    if trace:
        result["contexts"] = {"trace": {k: v for k, v in trace.items() if k in SAFE_TRACE}}
    return result


def sanitize_event(event, hint):
    result = common(event)
    result["level"] = event.get("level", "error")
    result["message"] = safe_message(event.get("message"))
    tags = {}
    supplied = event.get("tags", {})
    try:
        tags["run_id"] = str(UUID(str(supplied["run_id"])))
    except (KeyError, ValueError, TypeError):
        pass
    if supplied.get("provider") in {"cpsc", "brightdata", "gemini", "openai", "rules"}:
        tags["provider"] = supplied["provider"]
    result["tags"] = tags
    exceptions = []
    for exception in event.get("exception", {}).get("values", []):
        frames = []
        for frame in exception.get("stacktrace", {}).get("frames", []):
            clean = {k: v for k, v in frame.items() if k in SAFE_FRAME}
            if "filename" in clean:
                clean["filename"] = str(clean["filename"]).split("?")[0]
            if "context_line" in clean:
                clean["context_line"] = scrub_source(clean["context_line"])
            for context in ["pre_context", "post_context"]:
                if context in clean:
                    clean[context] = [scrub_source(line) for line in clean[context]]
            frames.append(clean)
        kind = exception.get("type", "Error")
        exceptions.append(
            {
                "type": kind if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]{0,100}", kind) else "Error",
                "value": safe_message(exception.get("value")),
                "stacktrace": {"frames": frames},
                "mechanism": {
                    "type": "generic",
                    "handled": exception.get("mechanism", {}).get("handled", False),
                },
            }
        )
    if exceptions:
        result["exception"] = {"values": exceptions}
    return result


def sanitize_transaction(event, hint):
    result = common(event)
    result.update(type="transaction", transaction="Sueperman request")
    for key in ["start_timestamp", "transaction_info"]:
        if key in event:
            result[key] = event[key]
    spans = []
    for span in event.get("spans", []):
        clean = {k: v for k, v in span.items() if k in SAFE_TRACE | {"start_timestamp", "timestamp"}}
        clean["description"] = span.get("op", "operation")
        clean["data"] = {}
        spans.append(clean)
    result["spans"] = spans
    return result


def sanitize_log(log, hint):
    body = log.get("body", "")
    if body != "Sueperman run requires attention" and not VERIFICATION.fullmatch(str(body)):
        return None
    log["attributes"] = {}
    return log


def initialize_telemetry(dsn, environment="development"):
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.httpx import HttpxIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release="sueperman@0.1.0",
        data_collection={
            "user_info": False,
            "cookies": {"mode": "off"},
            "http_headers": {"request": {"mode": "off"}},
            "http_bodies": [],
            "url_query_params": {"mode": "off"},
            "graphql": {"document": False, "variables": False},
            "gen_ai": {"inputs": False, "outputs": False},
            "database_query_data": False,
            "queues": False,
            "stack_frame_variables": False,
            "frame_context_lines": 2,
        },
        include_local_variables=False,
        default_integrations=False,
        auto_enabling_integrations=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            HttpxIntegration(),
        ],
        traces_sample_rate=0.1 if environment == "production" else 1.0,
        enable_logs=True,
        before_send=sanitize_event,
        before_send_transaction=sanitize_transaction,
        before_send_log=sanitize_log,
    )


def record_failure(dsn, run_id):
    if not dsn:
        return
    import sentry_sdk
    from sentry_sdk import logger

    with sentry_sdk.new_scope() as scope:
        scope.set_tag("run_id", run_id)
        sentry_sdk.capture_message("Sueperman run requires attention", level="error")
        logger.error("Sueperman run requires attention")
