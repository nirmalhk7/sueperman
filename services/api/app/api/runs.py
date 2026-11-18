from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import jobs
from app.agent.orchestrator import execute, run_view
from app.db import view
from app.diwali.band_settings import credentials as band_credentials
from app.diwali.band_settings import validate_synthetic
from app.diwali.coordinator import execute as execute_diwali
from app.models import (
    AgentRun,
    AuditEvent,
    Purchase,
    now,
)
from app.schemas import AuditResponse, RunRequest, RunResponse


def register(app, factory, settings, get):
    @app.post("/api/runs", response_model=RunResponse)
    def start(body: RunRequest, background: BackgroundTasks):
        if body.mode == "demo" and not settings.demo_mode:
            raise HTTPException(422, "Demo mode disabled")
        with factory() as s:
            s.connection().exec_driver_sql("BEGIN IMMEDIATE")
            old = s.scalar(select(AgentRun).where(AgentRun.idempotency_key == body.idempotency_key))
            if old:
                if (old.payload["purchase_ids"] != body.purchase_ids or old.payload["mode"] != body.mode
                        or old.payload.get("collaboration_mode", "deterministic") != body.collaboration_mode
                        or old.payload.get("fallback_of") != body.fallback_of):
                    raise HTTPException(409, "Idempotency key already used for different input")
                if old.payload.get("allow_recorded_fallback", True) != body.allow_recorded_fallback:
                    raise HTTPException(409, "Idempotency key already used for different input")
                return run_view(old)
            if body.collaboration_mode != "deterministic":
                if not settings.diwali_enabled:
                    raise HTTPException(403, "Diwali collaboration disabled")
                if body.collaboration_mode == "band":
                    try:
                        from app.diwali.band_bridge import BandTransport
                        BandTransport(band_credentials(settings))
                    except (ValueError, OSError, TypeError, KeyError):
                        raise HTTPException(503, "Bounded operator BAND configuration unavailable") from None
                if body.mode != "demo" or len(body.purchase_ids) > 5:
                    raise HTTPException(422, "Local collaboration requires at most five synthetic demo purchases")
                if len(body.purchase_ids) != len(set(body.purchase_ids)):
                    raise HTTPException(422, "One case per unique purchase is required")
            for identifier in body.purchase_ids:
                purchase = get(s, Purchase, identifier)
                if body.mode == "live" and not body.allow_recorded_fallback and purchase.demo:
                    raise HTTPException(422, "Only imported purchases can be investigated in this workspace")
                if body.collaboration_mode != "deterministic" and not purchase.demo:
                    raise HTTPException(422, "Local collaboration accepts synthetic demo data only")
            if body.collaboration_mode == "band":
                try:
                    validate_synthetic(s, body.purchase_ids)
                except (ValueError, KeyError):
                    raise HTTPException(422, "BAND accepts exact synthetic fixture content only") from None
            if s.scalar(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))):
                raise HTTPException(409, "A run is already active; wait before retrying")
            run = AgentRun(
                idempotency_key=body.idempotency_key,
                demo=body.mode == "demo",
                payload={
                    "purchase_ids": body.purchase_ids,
                    "mode": body.mode,
                    "allow_recorded_fallback": body.allow_recorded_fallback,
                    "started_at": now(),
                    "summary": {},
                    "opportunities": [],
                    "warnings": [],
                    "provider_modes": {},
                },
            )
            if body.collaboration_mode != "deterministic":
                run.payload = run.payload | {"collaboration_mode": body.collaboration_mode,
                    "actual_transport": "local" if body.collaboration_mode == "local" else None, "source_mode": "recorded", "reviewer_mode": "rules"}
            if body.fallback_of is not None:
                get(s, AgentRun, body.fallback_of)
                run.payload = run.payload | {"fallback_of": body.fallback_of}
            s.add(run)
            jobs.enqueue(run, settings)
            try:
                s.commit()
            except IntegrityError:
                s.rollback()
                raise HTTPException(409, "Duplicate run trigger") from None
            background.add_task(execute_diwali if body.collaboration_mode != "deterministic" else execute,
                                factory, run.id, settings)
            return run_view(run)

    @app.get("/api/runs/{identifier}", response_model=RunResponse)
    def run_detail(identifier: str):
        with factory() as s:
            return run_view(get(s, AgentRun, identifier))

    @app.get("/api/runs/{identifier}/events", response_model=list[AuditResponse])
    def events(identifier: str):
        with factory() as s:
            get(s, AgentRun, identifier)
            return [
                view(e)
                for e in s.scalars(
                    select(AuditEvent).where(AuditEvent.run_id == identifier).order_by(AuditEvent.seq)
                )
            ]
