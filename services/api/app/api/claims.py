from datetime import date

from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.db import view
from app.diwali.legacy_bridge import invalidate_stale
from app.models import (
    ClaimPacket,
    Opportunity,
    now,
)
from app.p1 import obligations
from app.p1.monitoring import review_required
from app.schemas import Approval, PacketResponse


def draft_allowed(opportunity):
    data = opportunity.payload
    if opportunity.kind == "recall":
        return data["status"] == "verified_match"
    return (
        not data.get("simulated", True)
        and data.get("preparation_only") is True
        and data.get("sources_verified") is True
        and data["status"] in {"uncertain", "eligible_candidate"}
        and date.today() <= date.fromisoformat(data["deadline_at"])
    )


def register(app, factory, get, settings=None):
    def p1_guard(session, packet):
        opportunity = get(session, Opportunity, packet.opportunity_id)
        if opportunity.payload.get("stale"):
            raise HTTPException(409, "Purchase corrected; recheck and review a new draft")
        if review_required(session, opportunity):
            raise HTTPException(409, "Current official source requires a new live review")
        if settings and settings.p1_enabled and obligations.invalidate_approval(session, packet):
            session.commit()
            raise HTTPException(409, "Current purchase, evidence or checklist requires a new review")
    @app.post("/api/opportunities/{identifier}/claim-packet", response_model=PacketResponse)
    def prepare(identifier: str):
        with factory() as s:
            o = get(s, Opportunity, identifier)
            if o.payload.get("stale"):
                raise HTTPException(409, "Purchase corrected; recheck and review a new draft")
            if not draft_allowed(o):
                raise HTTPException(409, "Hard gates have not passed; no real remedy packet available")
            packet = s.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == identifier))
            if packet is None:
                raise HTTPException(409, "Packet not yet prepared; wait for run completion")
            return view(packet)

    @app.get("/api/claim-packets/{identifier}", response_model=PacketResponse)
    def packet_detail(identifier: str):
        with factory() as s:
            return view(get(s, ClaimPacket, identifier))

    @app.post("/api/claim-packets/{identifier}/approve-local", response_model=PacketResponse)
    def approve(identifier: str, body: Approval):
        with factory() as s:
            s.connection().exec_driver_sql("BEGIN IMMEDIATE")
            packet = get(s, ClaimPacket, identifier)
            if invalidate_stale(s, identifier):
                s.commit()
                raise HTTPException(409, "Current purchase or evidence requires a new review")
            opportunity = get(s, Opportunity, packet.opportunity_id)
            p1_guard(s, packet)
            if (
                not draft_allowed(opportunity)
                or packet.payload["status"] == "needs_evidence"
            ):
                raise HTTPException(409, "Current official evidence requires a new review")
            packet.payload = packet.payload | {
                "status": "approved_local",
                "approved_at": now(),
                "reviewed_at": now(),
            }
            if settings and settings.p1_enabled and opportunity.kind == "recall":
                packet.payload = packet.payload | {"p1_approval_binding": obligations.approval_binding(s, packet)}
            s.commit()
            return view(packet)

    @app.post("/api/claim-packets/{identifier}/export")
    def export(identifier: str):
        with factory() as s:
            s.connection().exec_driver_sql("BEGIN IMMEDIATE")
            packet = get(s, ClaimPacket, identifier)
            if invalidate_stale(s, identifier):
                s.commit()
                raise HTTPException(409, "Current purchase or evidence requires a new review")
            opportunity = get(s, Opportunity, packet.opportunity_id)
            p1_guard(s, packet)
            if (
                not draft_allowed(opportunity)
                or packet.payload["status"] == "needs_evidence"
            ):
                raise HTTPException(409, "Current official evidence requires a new review")
            if packet.payload["status"] not in {"approved_local", "exported"}:
                raise HTTPException(409, "Approve draft locally before export")
            markdown = packet.payload["markdown"]
            if settings and settings.p1_enabled:
                markdown += obligations.appendix(s, packet)
            packet.payload = packet.payload | {"status": "exported"}
            s.commit()
            return Response(
                markdown,
                media_type="text/markdown",
                headers={"Content-Disposition": 'attachment; filename="sueperman-draft.md"'},
            )
