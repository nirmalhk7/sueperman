"""Prevent developer credentials from causing live traffic during deterministic tests."""

import pytest


@pytest.fixture(autouse=True)
def offline_provider_environment(monkeypatch):
    for key in [
        "SENTRY_DSN",
        "OPENAI_API_KEY",
        "GEMINI_API_KEY",
        "BRIGHTDATA_API_TOKEN",
        "SYSTEM_ONE_API_KEY",
    ]:
        monkeypatch.setenv(key, "")
    for key in [
        "OPENAI_ENABLED",
        "CPSC_LIVE_ENABLED",
        "GEMINI_ENABLED",
        "BRIGHTDATA_ENABLED",
        "SYSTEM_ONE_ENABLED",
    ]:
        monkeypatch.setenv(key, "false")
