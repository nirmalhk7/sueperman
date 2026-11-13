from datetime import date

from fastapi import HTTPException
from fastapi.responses import Response
from sqlalchemy import select

from app.db import view
from app.models import (
    ClaimPacket,
    Opportunity,
    now,
)
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


def register(app, factory, get):
    @app.post("/api/opportunities/{identifier}/claim-packet", response_model=PacketResponse)
    def prepare(identifier: str):
        with factory() as s:
            o = get(s, Opportunity, identifier)
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
            packet = get(s, ClaimPacket, identifier)
            opportunity = get(s, Opportunity, packet.opportunity_id)
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
            s.commit()
            return view(packet)

    @app.post("/api/claim-packets/{identifier}/export")
    def export(identifier: str):
        with factory() as s:
            packet = get(s, ClaimPacket, identifier)
            opportunity = get(s, Opportunity, packet.opportunity_id)
            if (
                not draft_allowed(opportunity)
                or packet.payload["status"] == "needs_evidence"
            ):
                raise HTTPException(409, "Current official evidence requires a new review")
            if packet.payload["status"] not in {"approved_local", "exported"}:
                raise HTTPException(409, "Approve draft locally before export")
            markdown = packet.payload["markdown"]
            packet.payload = packet.payload | {"status": "exported"}
            s.commit()
            return Response(
                markdown,
                media_type="text/markdown",
                headers={"Content-Disposition": 'attachment; filename="sueperman-draft.md"'},
            )
