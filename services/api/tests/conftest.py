"""Prevent developer credentials from causing live traffic during deterministic tests."""

import pytest


@pytest.fixture(autouse=True)
def offline_provider_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_MAX_CALLS_PER_RUN", "3")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    for key in [
        "SENTRY_DSN",
        "AGENT37_API_KEY",
        "LYZR_API_KEY",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "BRIGHTDATA_API_TOKEN",
        "SYSTEM_ONE_API_KEY",
    ]:
        monkeypatch.setenv(key, "")
    for key in [
        "COLLABORATION_LIVE_ENABLED",
        "BAND_ENABLED",
        "AGENT37_ENABLED",
        "ADAL_ENABLED",
        "FINCH_ENABLED",
        "LYZR_ENABLED",
        "SETTLEMENT_LIVE_ENABLED",
        "OPENAI_ENABLED",
        "OPENAI_RECEIPT_ENABLED",
        "CPSC_LIVE_ENABLED",
        "GEMINI_ENABLED",
        "BRIGHTDATA_ENABLED",
        "SYSTEM_ONE_ENABLED",
    ]:
        monkeypatch.setenv(key, "false")

    monkeypatch.setenv("BAND_API_KEYS", "{}")
