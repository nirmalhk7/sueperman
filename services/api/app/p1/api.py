"""Opt-in local P1 controls. Operator permission never substitutes for user intent."""

from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app.models import ClaimPacket, Opportunity
from app.p1 import monitoring, obligations


class WatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = Field(strict=True)


class ReadinessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    binding: str = Field(pattern=r"^[a-f0-9]{64}$")
    item_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    ready: bool = Field(strict=True)
    confirmed: bool = Field(strict=True)

    @field_validator("confirmed")
    @classmethod
    def confirmation_required(cls, value):
        if value is not True:
            raise ValueError("Explicit confirmation required")
        return value


def register(app, factory, settings, get):
    def permitted():
        task = getattr(app.state, "p1_watch_task", None)
        return bool(settings.p1_enabled and settings.p1_monitor_enabled and settings.cpsc_live_enabled
                    and task is not None and not task.done())

    def guard():
        if not settings.p1_enabled:
            raise HTTPException(403, "P1 features disabled")

    def watch_view(session, opportunity_id):
        row = session.scalar(select(monitoring.SourceWatch).where(
            monitoring.SourceWatch.opportunity_id == opportunity_id))
        checks = [] if row is None else list(reversed(session.scalars(select(monitoring.SourceCheck).where(
            monitoring.SourceCheck.watch_id == row.id).order_by(monitoring.SourceCheck.sequence.desc()).limit(20)).all()))
        return {"id": row.id if row else None, "enabled": row.enabled if row else False,
            "status": row.status if row else "not_configured", "available": permitted(), "interval_hours": 24,
            "next_check_at": row.due_at if row and row.enabled else None,
            "last_checked_at": row.payload.get("last_checked_at") if row else None,
            "checks": [{"id": check.id, "sequence": check.sequence, **check.payload} for check in checks]}

    @app.get("/api/p1/status")
    def status():
        return {"enabled": settings.p1_enabled, "source_monitor_available": permitted()}

    @app.get("/api/opportunities/{identifier}/source-monitor")
    def source_monitor(identifier: str):
        guard()
        with factory() as session:
            get(session, Opportunity, identifier)
            return watch_view(session, identifier)

    @app.post("/api/opportunities/{identifier}/source-monitor")
    def set_source_monitor(identifier: str, body: WatchRequest):
        guard()
        if body.enabled and not permitted():
            raise HTTPException(503, "Operator has not enabled scheduled public source reads")
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            get(session, Opportunity, identifier)
            try:
                monitoring.set_watch(session, identifier, enabled=body.enabled, observed_at=datetime.now(UTC))
            except monitoring.WatchConflict as error:
                raise HTTPException(409, str(error)) from None
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
            return watch_view(session, identifier)

    @app.get("/api/claim-packets/{identifier}/obligations")
    def readiness(identifier: str):
        guard()
        with factory() as session:
            packet = get(session, ClaimPacket, identifier)
            try:
                return obligations.view(session, packet)
            except ValueError as error:
                raise HTTPException(422, str(error)) from None

    @app.post("/api/claim-packets/{identifier}/obligations")
    def set_readiness(identifier: str, body: ReadinessRequest):
        guard()
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            packet = get(session, ClaimPacket, identifier)
            try:
                obligations.set_ready(session, packet, expected_binding=body.binding, item_id=body.item_id,
                    ready=body.ready, observed_at=datetime.now(UTC))
                return obligations.view(session, packet)
            except obligations.StaleReadiness as error:
                raise HTTPException(409, str(error)) from None
            except ValueError as error:
                raise HTTPException(422, str(error)) from None
