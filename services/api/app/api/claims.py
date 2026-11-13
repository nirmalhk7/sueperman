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


def register(app, factory, get):
    @app.post("/api/opportunities/{identifier}/claim-packet", response_model=PacketResponse)
    def prepare(identifier: str):
        with factory() as s:
            o = get(s, Opportunity, identifier)
            if o.kind != "recall" or o.payload["status"] != "verified_match":
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
                opportunity.payload["status"] != "verified_match"
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
                opportunity.payload["status"] != "verified_match"
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
