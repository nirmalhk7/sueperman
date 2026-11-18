"""Plan and stage associated-record erasure; callers own intent and commit."""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import inspect, select, update

from app import deletion, jobs
from app.diwali.persistence import CaseRow
from app.models import (
    AgentRun,
    CaseRecord,
    ClaimPacket,
    CollaborationRun,
    Opportunity,
    Product,
    Purchase,
    now,
)
from app.p1.monitoring import SourceWatch


class DeletionConflict(ValueError):
    pass


class PurchaseNotFound(ValueError):
    pass


@dataclass(frozen=True)
class DeletionPlan:
    purchase_id: str
    product_ids: frozenset[str]
    run_ids: frozenset[str]
    shared_run_ids: frozenset[str]
    affected_opportunity_ids: frozenset[str]
    affected_packet_ids: frozenset[str]
    investigations: int
    binding: str
    active: bool
    demo: bool

    def public(self):
        return {"purchase_id": self.purchase_id, "binding": self.binding,
                "shared_investigations": len(self.shared_run_ids), "investigations": self.investigations,
                "other_drafts_requiring_new_check": len(self.affected_packet_ids),
                "active": self.active,
                "blocked_reason": "Wait for the related investigation or source check to finish" if self.active else None}


def _strings(value):
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def _produced_at(run):
    # Legacy coordinators omit completion time. Serialized admission makes
    # immutable creation order a safer fallback than metadata's updated_at.
    return datetime.fromisoformat(run.payload.get("completed_at") or run.created_at)


def plan_purchase(session, identifier, *, require_purchase=True):
    purchase = session.get(Purchase, identifier)
    if purchase is None and require_purchase:
        raise PurchaseNotFound("Purchase not found")
    products = session.scalars(select(Product).where(Product.purchase_id == identifier)).all()
    product_ids = {product.id for product in products}
    all_runs = session.scalars(select(AgentRun)).all()
    runs = [run for run in all_runs
            if identifier in _strings(run.payload.get("purchase_ids"))]
    run_ids = {run.id for run in runs}
    shared = {run.id for run in runs if _strings(run.payload.get("purchase_ids")) - {identifier}}
    # Opportunities keep their own facts/evidence; the run stores membership.
    candidates = set().union(*(_strings(run.payload.get("opportunities")) for run in runs)) if runs else set()
    incomplete = [run for run in runs if run.status == "partial"]
    ambiguous: dict[str, list[AgentRun]] = {}
    for run in incomplete:
        # A cancelled legacy run may have committed findings before its final
        # opportunity-ID list. Do not treat missing membership as proof that
        # retained drafts are independent of this erased history.
        members = _strings(run.payload.get("purchase_ids")) - {identifier}
        for opportunity_id in session.scalars(select(Opportunity.id).join(Product).where(Product.purchase_id.in_(members))):
            ambiguous.setdefault(opportunity_id, []).append(run)
    candidates.update(ambiguous)
    associated_opportunities = set()
    for opportunity_id in candidates:
        producers = [run for run in all_runs if run.status in {"completed", "partial"}
                     and opportunity_id in _strings(run.payload.get("opportunities"))]
        latest = max(producers, key=lambda run: (_produced_at(run), run.id)) if producers else None
        if ((latest is not None and latest.id in run_ids)
                or (opportunity_id in ambiguous and (latest is None
                    or _produced_at(latest) <= max(_produced_at(run) for run in ambiguous[opportunity_id])))):
            associated_opportunities.add(opportunity_id)
    # An older retained draft may still bind a removed Builder case even when
    # its opportunity was evaluated again by an independent run.
    if inspect(session.connection()).has_table(CaseRow.__tablename__):
        erased_cases = set(session.scalars(select(CaseRow.id).where(CaseRow.run_id.in_(run_ids))))
        for packet in session.scalars(select(ClaimPacket)):
            case_id = packet.payload.get("diwali_case_id")
            if isinstance(case_id, str) and case_id in erased_cases:
                associated_opportunities.add(packet.opportunity_id)
    cases = session.scalars(select(CaseRecord).where(CaseRecord.product_id.in_(product_ids))).all()
    teams = session.scalars(select(CollaborationRun).where(CollaborationRun.case_id.in_([case.id for case in cases]))).all()
    own_opportunities = session.scalars(select(Opportunity).where(Opportunity.product_id.in_(product_ids))).all()
    watches = []
    if inspect(session.connection()).has_table(SourceWatch.__tablename__):
        watches = session.scalars(select(SourceWatch).where(
            SourceWatch.opportunity_id.in_([opportunity.id for opportunity in own_opportunities]))).all()
    active = any(run.status in jobs.ACTIVE for run in [*runs, *teams]) or any(watch.status == "checking" for watch in watches)
    others = session.scalars(select(Opportunity).where(Opportunity.id.in_(associated_opportunities),
                                                       Opportunity.product_id.not_in(product_ids))).all()
    packets = session.scalars(select(ClaimPacket).where(ClaimPacket.opportunity_id.in_([row.id for row in others]))).all()
    revision = {"purchase": [identifier, purchase.updated_at if purchase else None],
                "products": sorted((product.id, product.updated_at) for product in products),
                "runs": sorted((run.id, run.status, run.updated_at) for run in runs),
                "teams": sorted((run.id, run.status, run.updated_at) for run in teams),
                "watches": sorted((watch.id, watch.status, watch.updated_at) for watch in watches),
                "opportunities": sorted(associated_opportunities),
                "other_drafts": sorted((packet.id, packet.updated_at) for packet in packets)}
    return DeletionPlan(purchase_id=identifier, product_ids=frozenset(product_ids), run_ids=frozenset(run_ids),
                        shared_run_ids=frozenset(shared), affected_opportunity_ids=frozenset(associated_opportunities),
                        affected_packet_ids=frozenset(packet.id for packet in packets), investigations=len(runs) + len(teams),
                        binding=hashlib.sha256(json.dumps(revision, sort_keys=True).encode()).hexdigest(),
                        active=active, demo=purchase.demo if purchase else False)


def erase_purchase(session, plan, *, recovering=False):
    """Preserve other purchases/findings; invalidate drafts losing their provenance.

    Shared-history consent is enforced by the HTTP coordinator before recording
    intent. Startup recovery applies that already-recorded scope before workers.
    """
    if plan.active and not recovering:
        raise DeletionConflict("Wait for the related investigation or source check to finish")
    others = session.scalars(select(Opportunity).where(Opportunity.id.in_(plan.affected_opportunity_ids),
                                                       Opportunity.product_id.not_in(plan.product_ids))).all()
    for opportunity in others:
        session.execute(update(Opportunity).where(Opportunity.id == opportunity.id).values(
            payload=opportunity.payload | {"stale": True, "stale_reason": "related_history_removed"}, updated_at=now()))
        for packet in session.scalars(select(ClaimPacket).where(ClaimPacket.opportunity_id == opportunity.id)):
            session.execute(update(ClaimPacket).where(ClaimPacket.id == packet.id).values(payload=packet.payload | {
                "status": "needs_evidence", "approved_at": None, "reviewed_at": None,
                "p1_approval_binding": None, "diwali_case_id": None}, updated_at=now()))
    # A retained fallback may reference this history, but cannot retain its ID.
    for run in session.scalars(select(AgentRun)):
        if run.id not in plan.run_ids and run.payload.get("fallback_of") in plan.run_ids:
            session.execute(update(AgentRun).where(AgentRun.id == run.id).values(
                payload=run.payload | {"fallback_of": None}, updated_at=now()))
    counts = deletion.purge_roots(session, "agent_runs", plan.run_ids)
    for name, count in deletion.purge_purchase(session, plan.purchase_id).items():
        counts[name] = counts.get(name, 0) + count
    return counts
