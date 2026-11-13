from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, select

from app.config import ROOT
from app.models import (
    AgentRun,
    AuditEvent,
    ClaimPacket,
    EligibilityAssessment,
    Opportunity,
    Product,
    Purchase,
    SourceEvidence,
)
from app.schemas import ImportResponse


def register(app, factory, settings, import_products):
    @app.post("/api/demo/reset", response_model=ImportResponse)
    def reset():
        if not settings.demo_mode:
            raise HTTPException(404, "Demo mode disabled")
        with factory() as s:
            if s.scalar(select(AgentRun).where(AgentRun.status.in_(["running", "queued"]))):
                raise HTTPException(409, "Wait for active run before reset")
            demo_models: list[type[Any]] = [
                AuditEvent,
                ClaimPacket,
                EligibilityAssessment,
                SourceEvidence,
                Opportunity,
                AgentRun,
                Product,
                Purchase,
            ]
            for model in demo_models:
                s.execute(delete(model).where(model.demo.is_(True)))
            s.commit()
            return import_products(s, (ROOT / "demo/orders.csv").read_bytes(), demo=True)
