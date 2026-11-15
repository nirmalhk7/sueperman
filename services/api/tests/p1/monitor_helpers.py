"""Shared monitor test inputs; no production-only test hooks."""

import importlib
from datetime import UTC, datetime

import pytest

NOW = datetime(2026, 11, 15, 12, tzinfo=UTC)


def monitor():
    try:
        return importlib.import_module("app.p1.monitoring")
    except ModuleNotFoundError:
        pytest.fail("Persistent P1 source monitoring is not implemented")




def enable(module, engine, factory, opportunity_id):
    module.setup_schema(engine)
    with factory.begin() as s:
        row = module.set_watch(s, opportunity_id, enabled=True, observed_at=NOW)
        return row.id
