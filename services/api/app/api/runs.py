from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.agent.orchestrator import execute, run_view
from app.db import view
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
            old = s.scalar(select(AgentRun).where(AgentRun.idempotency_key == body.idempotency_key))
            if old:
                if old.payload["purchase_ids"] != body.purchase_ids or old.payload["mode"] != body.mode:
                    raise HTTPException(409, "Idempotency key already used for different input")
                return run_view(old)
            for identifier in body.purchase_ids:
                get(s, Purchase, identifier)
            if s.scalar(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))):
                raise HTTPException(409, "A run is already active; wait before retrying")
            run = AgentRun(
                idempotency_key=body.idempotency_key,
                demo=body.mode == "demo",
                payload={
                    "purchase_ids": body.purchase_ids,
                    "mode": body.mode,
                    "started_at": now(),
                    "summary": {},
                    "opportunities": [],
                    "warnings": [],
                    "provider_modes": {},
                },
            )
            s.add(run)
            try:
                s.commit()
            except IntegrityError:
                s.rollback()
                raise HTTPException(409, "Duplicate run trigger") from None
            background.add_task(execute, factory, run.id, settings)
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
