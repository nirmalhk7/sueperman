from uuid import UUID


def sanitize_event(event, hint):
    """Only explicit operational metadata may cross the telemetry boundary."""
    tags = {}
    supplied = event.get("tags", {})
    try:
        tags["run_id"] = str(UUID(str(supplied["run_id"])))
    except (KeyError, ValueError, TypeError):
        pass
    if supplied.get("provider") in {"cpsc", "brightdata", "gemini", "system_one", "rules"}:
        tags["provider"] = supplied["provider"]
    return {
        "event_id": event.get("event_id"),
        "level": "error",
        "message": "Sueperman run requires attention",
        "tags": tags,
    }


def initialize_telemetry(dsn):
    if not dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=False,
        include_local_variables=False,
        default_integrations=False,
        auto_enabling_integrations=False,
        before_send=sanitize_event,
    )


def record_failure(dsn, run_id):
    if not dsn:
        return
    import sentry_sdk

    with sentry_sdk.new_scope() as scope:
        scope.set_tag("run_id", run_id)
        sentry_sdk.capture_message("Sueperman run requires attention", level="error")
