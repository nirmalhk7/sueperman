"""Version-bound, self-reported evidence readiness. No declarations or uploads."""

import hashlib
from pathlib import Path

from sqlalchemy import ForeignKey, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column

from app.matching.recall import match_recall
from app.models import ClaimPacket, Entity, Opportunity, Product, SourceEvidence
from app.p1.monitoring import P1Base, digest, review_required
from app.schemas import ProductInput, RecallRecord


class ObligationState(Entity, P1Base):
    __tablename__ = "p1_obligation_states"
    packet_id: Mapped[str] = mapped_column(ForeignKey(ClaimPacket.id, ondelete="CASCADE"))
    binding: Mapped[str]
    __table_args__ = (UniqueConstraint("packet_id", "binding"),)


class StaleReadiness(ValueError):
    pass


def policy_digest():
    return hashlib.sha256(Path(__file__).with_name("normalizers.json").read_bytes()
                          + b"obligation-readiness-v1").hexdigest()


def inputs(session, packet):
    opportunity = session.get(Opportunity, packet.opportunity_id)
    if opportunity.kind != "recall":
        raise ValueError("Readiness checklist is available for recall drafts only")
    product = session.get(Product, opportunity.product_id)
    evidence = session.scalars(select(SourceEvidence).where(SourceEvidence.opportunity_id == opportunity.id)).all()
    return opportunity, product, evidence


def binding(session, packet):
    opportunity, product, evidence = inputs(session, packet)
    return digest({"packet_id": packet.id, "markdown": packet.payload["markdown"],
        "required_documents": packet.payload["required_documents"], "product": product.payload["product"],
        "recall": {k: v for k, v in opportunity.payload["recall"].items() if k not in {"fetched_at", "mode"}},
        "sources": sorted((e.url, e.payload.get("quoted_excerpt"), e.payload.get("content_sha256")) for e in evidence),
        "policy": policy_digest()})


def eligible(session, packet):
    opportunity, product, evidence = inputs(session, packet)
    try:
        recall = RecallRecord.model_validate(opportunity.payload["recall"])
        result = match_recall(ProductInput.model_validate(product.payload["product"]), recall)
        government = [e for e in evidence if e.payload.get("source_type") == "government"]
        return (not review_required(session, opportunity, recall)
            and opportunity.payload["status"] == "verified_match" and result.status == "verified_match"
            and bool(government) and all(e.url == recall.official_url
                and e.payload.get("quoted_excerpt") == recall.excerpt
                and e.payload.get("content_sha256") == hashlib.sha256(recall.excerpt.encode()).hexdigest()
                for e in government))
    except (ValueError, KeyError, TypeError):
        return False


def state_for(session, packet, current):
    return session.scalar(select(ObligationState).where(
        ObligationState.packet_id == packet.id, ObligationState.binding == current))


def items(packet):
    return [{"id": digest([i, label]), "label": label}
            for i, label in enumerate(packet.payload["required_documents"])]


def view(session, packet):
    current = binding(session, packet)
    state = state_for(session, packet, current)
    values = state.payload.get("items", {}) if state else {}
    return {"binding": current, "mode": "self_reported", "eligible": eligible(session, packet),
        "items": [item | values.get(item["id"], {"ready": False, "confirmed_at": None}) for item in items(packet)],
        "previous_versions": len(session.scalars(select(ObligationState).where(
            ObligationState.packet_id == packet.id, ObligationState.binding != current)).all())}


def set_ready(session, packet, *, expected_binding, item_id, ready, observed_at):
    current = binding(session, packet)
    if current != expected_binding or not eligible(session, packet):
        raise StaleReadiness("Purchase, evidence or rules changed; review current sources")
    if item_id not in {item["id"] for item in items(packet)}:
        raise ValueError("Unknown evidence-readiness item")
    state = state_for(session, packet, current)
    if state is None:
        state = ObligationState(packet_id=packet.id, binding=current, demo=packet.demo, payload={"items": {}})
        session.add(state)
        session.flush()
    values = state.payload["items"]
    if values.get(item_id, {}).get("ready", False) == ready:
        return
    state.payload = state.payload | {"items": values | {
        item_id: {"ready": ready, "confirmed_at": observed_at.isoformat()}}}
    packet.payload = packet.payload | {"status": "ready_for_review", "approved_at": None,
        "reviewed_at": None, "p1_approval_binding": None}


def approval_binding(session, packet):
    current = binding(session, packet)
    state = state_for(session, packet, current)
    return digest({"inputs": current, "readiness": state.payload if state else {}})


def invalidate_approval(session, packet):
    opportunity = session.get(Opportunity, packet.opportunity_id)
    if opportunity.kind != "recall":
        return False
    saved = packet.payload.get("p1_approval_binding")
    if not eligible(session, packet) or (saved and saved != approval_binding(session, packet)):
        packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None,
            "reviewed_at": None, "p1_approval_binding": None}
        return True
    return False


def appendix(session, packet):
    opportunity = session.get(Opportunity, packet.opportunity_id)
    if opportunity.kind != "recall":
        return ""
    current = view(session, packet)
    if state_for(session, packet, current["binding"]) is None:
        return ""
    lines = ["", "## Evidence readiness — self-reported, not verified",
             "No declaration or submission is recorded. Required proof remains your responsibility."]
    lines += [f"- [{'x' if item['ready'] else ' '}] {'Ready locally' if item['ready'] else 'Still needed'}: {item['label']}"
              for item in current["items"]]
    return "\n".join(lines)
