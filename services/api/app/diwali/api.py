"""Read-only accepted-message timeline and cached integration configuration."""

from fastapi import HTTPException, Query
from sqlalchemy import select

from app.config import ROOT
from app.diwali.persistence import MessageRow
from app.models import AgentRun, Purchase


def register(app, factory, settings, get, import_products):
    @app.post("/api/demo/diwali/reset")
    def reset():
        if not settings.diwali_enabled or not settings.diwali_operator_demo:
            raise HTTPException(403, "Isolated operator demo reset disabled")
        with factory() as session:
            if session.scalar(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))):
                raise HTTPException(409, "Wait for active run before reset")
            if session.scalar(select(Purchase).where(Purchase.demo.is_(False))):
                raise HTTPException(409, "Use an isolated demo database; private purchases are present")
            return import_products(session, (ROOT / "demo/orders.csv").read_bytes(), demo=True)

    @app.get("/api/runs/{identifier}/agent-messages")
    def messages(identifier: str, after_seq: int = Query(default=0, ge=0), limit: int = Query(default=100, ge=1, le=100)):
        with factory() as session:
            get(session, AgentRun, identifier)
            rows = session.scalars(select(MessageRow).where(
                MessageRow.run_id == identifier, MessageRow.seq > after_seq,
                MessageRow.delivery == "consumed").order_by(MessageRow.seq).limit(limit)).all()
            items = [{"seq": r.seq, "transport": r.payload["transport"], **r.payload["envelope"]} for r in rows]
            return {"items": items, "next_seq": rows[-1].seq if rows else after_seq}

    @app.get("/api/integrations/diwali/status")
    def status():
        configured = {"band": bool(settings.band_credentials_file),
                      "lyzr": bool(settings.lyzr_api_key and settings.lyzr_review_agent_id),
                      "finch": bool(settings.finch_skill_path and settings.finch_skill_sha256),
                      "agent37": bool(settings.agent37_api_key and settings.agent37_instance_id), "adal": False}
        return {"enabled": settings.diwali_enabled, "providers": [
            {"name": name, "configured": configured[name], "enabled": getattr(settings, name + "_enabled", False), "healthy": None,
             "last_observed_at": None, "proof": "NOT_STARTED"}
            for name in ("band", "lyzr", "finch", "agent37", "adal")]}
