"""Prevent developer credentials from causing live traffic during deterministic tests."""

import pytest


@pytest.fixture(autouse=True)
def offline_provider_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_CALLS_PER_RUN", "3")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    for key in [
        "SENTRY_DSN",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "BRIGHTDATA_API_TOKEN",
        "SYSTEM_ONE_API_KEY",
    ]:
        monkeypatch.setenv(key, "")
    for key in [
        "SETTLEMENT_LIVE_ENABLED",
        "OPENAI_ENABLED",
        "OPENAI_RECEIPT_ENABLED",
        "CPSC_LIVE_ENABLED",
        "GEMINI_ENABLED",
        "BRIGHTDATA_ENABLED",
        "SYSTEM_ONE_ENABLED",
        "P1_ENABLED",
        "P1_MONITOR_ENABLED",
    ]:
        monkeypatch.setenv(key, "false")
