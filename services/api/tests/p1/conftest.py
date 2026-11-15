"""Populated V1 graph for additive P1 acceptance checks."""

import pytest
from fastapi.testclient import TestClient
from monitor_helpers import NOW
from sqlalchemy import select

from app.db import database
from app.models import ClaimPacket, Opportunity
from app.schemas import RecallRecord


@pytest.fixture
def graph(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/default.db")
    from app.main import create_app
    url = f"sqlite:///{tmp_path}/monitor.db"
    with TestClient(create_app(database_url=url)) as client:
        seed = client.post("/api/demo/reset").json()
        response = client.post("/api/runs", json={"purchase_ids": seed["purchase_ids"],
            "mode": "demo", "idempotency_key": "monitor-fixture"})
        assert response.status_code == 200
        engine, factory = database(url)
        with factory.begin() as s:
            packet = s.scalar(select(ClaimPacket))
            packet.payload = packet.payload | {"status": "approved_local", "approved_at": NOW.isoformat()}
            opportunity = s.get(Opportunity, packet.opportunity_id)
            record = RecallRecord.model_validate(opportunity.payload["recall"])
            identifiers = (opportunity.id, packet.id)
        yield engine, factory, client, *identifiers, record
        engine.dispose()

