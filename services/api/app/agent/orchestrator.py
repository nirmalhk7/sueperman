import asyncio
import hashlib
import json
from datetime import date
from time import monotonic
from urllib.parse import urlsplit

from sqlalchemy import delete, select

from app.agent.states import Stage
from app.claims.compose import compose, compose_settlement
from app.config import ROOT
from app.db import view
from app.matching.recall import match_recall
from app.matching.settlement import match_settlement, match_verified_settlement
from app.models import (
    AgentRun,
    AuditEvent,
    ClaimPacket,
    EligibilityAssessment,
    Opportunity,
    Product,
    SourceEvidence,
    now,
)
from app.providers.brightdata import BrightDataResearcher, ResearchEvidence
from app.providers.cpsc import CPSCRecallSource, FixtureRecallSource
from app.providers.errors import ProviderUnavailable
from app.providers.openai import OpenAIDecisionRouter
from app.providers.settlement import VerifiedSettlementSource
from app.providers.systemone import RulesRouter
from app.schemas import ProductInput, SettlementRecord
from app.telemetry import record_failure


def event(session, run, stage, outcome="ok", refs=None, provider="rules", entity_id=None, duration_ms=None):
    seq = len(session.scalars(select(AuditEvent).where(AuditEvent.run_id == run.id)).all()) + 1
    session.add(
        AuditEvent(
            run_id=run.id,
            seq=seq,
            demo=run.demo,
            payload={
                "seq": seq,
                "stage": str(stage),
                "action": str(stage).lower(),
                "outcome": outcome,
                "timestamp": now(),
                "duration_ms": duration_ms,
                "provider": provider,
                "source_refs": refs or [],
                "entity_id": entity_id,
                "redacted_details": {},
            },
        )
    )
    session.commit()


def persist_recall(session, entity, product, recall, result, decision, research):
    opp = session.scalar(
        select(Opportunity).where(
            Opportunity.product_id == entity.id,
            Opportunity.kind == "recall",
            Opportunity.source_id == recall.reference,
        )
    )
    if opp is None:
        opp = Opportunity(
            product_id=entity.id,
            kind="recall",
            source_id=recall.reference,
            official_url=recall.official_url,
            demo=entity.demo,
            payload={},
        )
        session.add(opp)
        session.flush()
    from app.p1.monitoring import review_required
    if review_required(session, opp, recall):
        session.commit()
        return opp
    opp.official_url = recall.official_url
    opp.payload = {
        "product_id": entity.id,
        "kind": "recall",
        "title": recall.title,
        "status": result.status,
        "official_url": recall.official_url,
        "source_id": recall.reference,
        "matching_reasons": result.reasons,
        "contrary_evidence": [c.model_dump(mode="json") for c in result.conditions if c.status == "false"],
        "source_observed_at": recall.fetched_at.isoformat(),
        "simulated": False,
        "mode": recall.mode,
        "remedy_kind": recall.remedy_kind,
        "recall": recall.model_dump(mode="json"),
    }
    session.execute(delete(SourceEvidence).where(SourceEvidence.opportunity_id == opp.id))
    session.add(
        SourceEvidence(
            opportunity_id=opp.id,
            url=recall.official_url,
            demo=entity.demo,
            payload={
                "url": recall.official_url,
                "domain": urlsplit(recall.official_url).hostname,
                "publisher": recall.publisher,
                "source_type": "government",
                "title": recall.title,
                "fetched_at": recall.fetched_at.isoformat(),
                "quoted_excerpt": recall.excerpt,
                "content_sha256": hashlib.sha256(recall.excerpt.encode()).hexdigest(),
                "extracted_facts": recall.model_dump(mode="json"),
                "authoritative_for": ["model", "remedy", "safety"],
            },
        )
    )
    if research is not None:
        session.add(
            SourceEvidence(
                opportunity_id=opp.id,
                url=research.url,
                demo=entity.demo,
                payload=research.model_dump(mode="json"),
            )
        )
    assessment = session.scalar(
        select(EligibilityAssessment).where(EligibilityAssessment.opportunity_id == opp.id)
    )
    if assessment is None:
        assessment = EligibilityAssessment(opportunity_id=opp.id, demo=entity.demo)
        session.add(assessment)
    assessment.payload = {
        "outcome": "eligible_candidate"
        if result.status == "verified_match"
        else "ineligible"
        if result.status == "rejected"
        else "uncertain",
        "hard_conditions": [c.model_dump(mode="json") for c in result.conditions],
        "missing_fields": [c.name for c in result.conditions if c.status == "unknown"],
        "reasons": result.reasons,
        "performed_by": "openai_assisted" if decision.mode == "openai" else "deterministic",
        "decision_raw_summary": decision.model_dump(),
        "evaluated_at": now(),
    }
    packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == opp.id))
    if result.status == "verified_match":
        composed = compose(product, recall) | {"generated_at": now()}
        if packet is None:
            session.add(ClaimPacket(opportunity_id=opp.id, demo=entity.demo, payload=composed))
        elif (
            packet.payload.get("markdown") != composed["markdown"]
            or packet.payload["status"] == "needs_evidence"
        ):
            packet.payload = composed
    elif packet is not None:
        packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None}
    session.commit()
    return opp


def persist_settlement(session, entity, product):
    rules = SettlementRecord(**json.loads((ROOT / "demo/settlement_fixture.json").read_text()))
    result = match_settlement(product, rules, date(2026, 11, 13))
    opp = session.scalar(
        select(Opportunity).where(Opportunity.product_id == entity.id, Opportunity.kind == "settlement")
    )
    if opp is None:
        opp = Opportunity(
            product_id=entity.id,
            kind="settlement",
            source_id=rules.source_url,
            official_url=rules.source_url,
            demo=True,
            payload={
                "product_id": entity.id,
                "kind": "settlement",
                "title": rules.title,
                "status": result.status,
                "matching_reasons": result.reasons,
                "simulated": True,
                "mode": "fixture",
                "source_id": rules.source_url,
                "official_url": rules.source_url,
                "source_observed_at": rules.fetched_at.isoformat(),
                "deadline_at": rules.deadline.isoformat(),
                "remedy_kind": "unknown",
                "evaluated_as_of": "2026-11-13",
            },
        )
        session.add(opp)
        session.flush()
        session.add(
            SourceEvidence(
                opportunity_id=opp.id,
                url=rules.source_url,
                demo=True,
                payload={
                    "url": rules.source_url,
                    "publisher": "Synthetic demo fixture",
                    "source_type": "fixture",
                    "fetched_at": rules.fetched_at.isoformat(),
                    "quoted_excerpt": "SIMULATED CASE — NO REAL CLAIM AVAILABLE",
                    "content_sha256": hashlib.sha256(rules.model_dump_json().encode()).hexdigest(),
                },
            )
        )
        session.add(
            EligibilityAssessment(
                opportunity_id=opp.id,
                demo=True,
                payload={
                    "outcome": result.status,
                    "hard_conditions": [c.model_dump(mode="json") for c in result.conditions],
                    "missing_fields": [],
                    "reasons": result.reasons,
                    "performed_by": "deterministic",
                    "evaluated_at": now(),
                },
            )
        )
        session.commit()
    return opp


def persist_verified_settlement(session, entity, product, rules):
    result = match_verified_settlement(product, rules, date.today())
    opp = session.scalar(
        select(Opportunity).where(
            Opportunity.product_id == entity.id,
            Opportunity.kind == "settlement",
            Opportunity.source_id == rules.case_number,
        )
    )
    if opp is None:
        opp = Opportunity(
            product_id=entity.id,
            kind="settlement",
            source_id=rules.case_number,
            official_url=rules.official_url,
            demo=entity.demo,
            payload={},
        )
        session.add(opp)
        session.flush()
    opp.payload = {
        "product_id": entity.id,
        "kind": "settlement",
        "title": rules.title,
        "status": result.status,
        "source_id": rules.case_number,
        "official_url": rules.official_url,
        "matching_reasons": result.reasons,
        "simulated": False,
        "mode": "live",
        "source_observed_at": rules.fetched_at.isoformat(),
        "deadline_at": rules.deadline.isoformat(),
        "remedy_kind": "unknown",
        "preparation_only": True,
        "sources_verified": True,
        "settlement": rules.model_dump(mode="json"),
    }
    session.execute(delete(SourceEvidence).where(SourceEvidence.opportunity_id == opp.id))
    for evidence in rules.evidence:
        session.add(
            SourceEvidence(
                opportunity_id=opp.id,
                url=evidence.url,
                demo=entity.demo,
                payload=evidence.model_dump(mode="json"),
            )
        )
    assessment = session.scalar(
        select(EligibilityAssessment).where(EligibilityAssessment.opportunity_id == opp.id)
    )
    if assessment is None:
        assessment = EligibilityAssessment(opportunity_id=opp.id, demo=entity.demo)
        session.add(assessment)
    assessment.payload = {
        "outcome": "ineligible" if result.status in {"expired", "ineligible"} else "uncertain",
        "hard_conditions": [c.model_dump(mode="json") for c in result.conditions],
        "missing_fields": [c.name for c in result.conditions if c.status == "unknown"],
        "reasons": result.reasons,
        "performed_by": "deterministic",
        "evaluated_at": now(),
    }
    packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == opp.id))
    if result.status == "uncertain":
        composed = compose_settlement(product, rules, result) | {"generated_at": now()}
        if packet is None:
            session.add(ClaimPacket(opportunity_id=opp.id, demo=entity.demo, payload=composed))
        else:
            packet.payload = composed
    elif packet is not None:
        packet.payload = packet.payload | {"status": "needs_evidence", "approved_at": None}
    session.commit()
    return opp


def invalidate_settlements(session, product_id):
    stale = session.scalars(
        select(Opportunity).where(Opportunity.product_id == product_id, Opportunity.kind == "settlement")
    ).all()
    ids = []
    for opp in stale:
        if opp.payload.get("simulated", True):
            continue
        reason = "Primary-source refresh unavailable; prior draft requires renewed verification."
        opp.payload = opp.payload | {
            "status": "unavailable",
            "sources_verified": False,
            "verification_failed_at": now(),
            "matching_reasons": list(dict.fromkeys([*opp.payload["matching_reasons"], reason])),
        }
        packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == opp.id))
        if packet is not None:
            packet.payload = packet.payload | {
                "status": "needs_evidence",
                "approved_at": None,
                "reviewed_at": None,
                "verification_status": "unavailable",
                "missing_documents": list(
                    dict.fromkeys(
                        [
                            *packet.payload["missing_documents"],
                            "Renew verification of official administrator and court sources",
                        ]
                    )
                ),
            }
        assessment = session.scalar(
            select(EligibilityAssessment).where(EligibilityAssessment.opportunity_id == opp.id)
        )
        if assessment is not None:
            conditions = [
                c for c in assessment.payload["hard_conditions"] if c["name"] != "current_primary_sources"
            ]
            assessment.payload = assessment.payload | {
                "outcome": "uncertain",
                "evaluated_at": now(),
                "hard_conditions": [
                    *conditions,
                    {
                        "name": "current_primary_sources",
                        "expected": "Reviewed current primary documents",
                        "observed": "Unavailable",
                        "status": "unknown",
                        "source_id": opp.official_url,
                    },
                ],
                "missing_fields": list(
                    dict.fromkeys([*assessment.payload["missing_fields"], "current_primary_sources"])
                ),
            }
        ids.append(opp.id)
    session.commit()
    return ids


async def execute(factory, run_id, settings):
    with factory() as session:
        run = session.get(AgentRun, run_id)
        if run is None:
            return
        run.status = "running"
        session.commit()
        event(session, run, Stage.RECEIVED)
        ids, warnings = [], []
        modes = {"receipt": "csv", "recall": "replay", "research": "disabled", "decision": "rules"}
        products = session.scalars(
            select(Product).where(Product.purchase_id.in_(run.payload["purchase_ids"]))
        ).all()
        live = run.payload["mode"] == "live"
        source: FixtureRecallSource | CPSCRecallSource = FixtureRecallSource()
        research_cache: dict[str, ResearchEvidence | None] = {}
        settlements = VerifiedSettlementSource()
        model_calls = 0
        router = (
            OpenAIDecisionRouter(settings.openai_api_key, settings.openai_decision_model)
            if live and settings.openai_enabled
            else RulesRouter()
        )
        try:
            async with asyncio.timeout(90):
                event(session, run, Stage.PARSED)
                event(session, run, Stage.PRODUCT_NORMALIZED)
                if live:
                    if settings.cpsc_live_enabled:
                        source = CPSCRecallSource(reviewed_notices=settings.p1_enabled)
                        modes["recall"] = "cpsc"
                    elif settings.demo_mode:
                        warnings.append("LIVE PROVIDER UNAVAILABLE — DEMO DATA")
                        modes["recall"] = "replay_fallback"
                    else:
                        raise ProviderUnavailable("Live recall provider disabled")
                for entity in products:
                    product = ProductInput(**entity.payload["product"])
                    started = monotonic()
                    try:
                        records = await source.search(product)
                    except ProviderUnavailable:
                        if not settings.demo_mode:
                            raise
                        source = FixtureRecallSource()
                        modes["recall"] = "replay_fallback"
                        warnings.append("LIVE PROVIDER UNAVAILABLE — DEMO DATA")
                        records = await source.search(product)
                    if getattr(source, "truncated", False):
                        warnings.append(
                            "CPSC candidate search truncated to 10 records; refine product identifiers"
                        )
                    event(
                        session,
                        run,
                        Stage.CANDIDATES_FOUND,
                        refs=[r.reference for r in records],
                        provider=source.provider_name,
                        entity_id=entity.id,
                        duration_ms=round((monotonic() - started) * 1000),
                    )
                    for recall in records[:10]:
                        result = match_recall(product, recall)
                        event(
                            session,
                            run,
                            Stage.SOURCES_VERIFIED,
                            refs=[recall.official_url],
                            provider=source.provider_name,
                            entity_id=entity.id,
                        )
                        if (
                            isinstance(router, OpenAIDecisionRouter)
                            and model_calls >= settings.openai_max_calls_per_run
                        ):
                            decision = (await RulesRouter().route(result)).model_copy(
                                update={"mode": "rules_budget_fallback"}
                            )
                            warnings.append(
                                "OpenAI per-run call budget reached — deterministic rules retained"
                            )
                        else:
                            if isinstance(router, OpenAIDecisionRouter):
                                model_calls += 1
                            decision = await router.route(result)
                        modes["decision"] = decision.mode
                        if decision.mode == "rules_fallback":
                            warnings.append(
                                "OpenAI decision model unavailable — deterministic rules retained"
                            )
                        event(
                            session,
                            run,
                            Stage.INVESTIGATION_ROUTED,
                            outcome=decision.choice,
                            provider=decision.mode,
                            entity_id=entity.id,
                            refs=[recall.official_url],
                        )
                        if decision.choice == "request_user_info":
                            event(
                                session,
                                run,
                                Stage.NEEDS_INFO,
                                outcome="user_information_required",
                                provider=decision.mode,
                                entity_id=entity.id,
                            )
                        research = None
                        if (
                            live
                            and settings.brightdata_enabled
                            and (result.status == "verified_match" or decision.choice == "inspect_more")
                        ):
                            if recall.reference not in research_cache:
                                try:
                                    research_cache[recall.reference] = await BrightDataResearcher(
                                        settings.brightdata_api_token
                                    ).research(recall)
                                except ProviderUnavailable:
                                    research_cache[recall.reference] = None
                            research = research_cache[recall.reference]
                            modes["research"] = "brightdata" if research else "cpsc_only_fallback"
                            if research is None:
                                warnings.append("Bright Data unavailable — official CPSC facts retained")
                        opp = persist_recall(session, entity, product, recall, result, decision, research)
                        ids.append(opp.id)
                        event(
                            session,
                            run,
                            Stage.ELIGIBILITY_EVALUATED,
                            outcome=opp.payload["status"],
                            provider=decision.mode,
                            entity_id=opp.id,
                            refs=[recall.official_url],
                        )
                        if opp.payload["status"] == "verified_match":
                            event(
                                session,
                                run,
                                Stage.PACKET_PREPARED,
                                entity_id=opp.id,
                                refs=[recall.official_url],
                            )
                    if entity.demo and product.model_number == "DC-EARBUDS-1":
                        opp = persist_settlement(session, entity, product)
                        ids.append(opp.id)
                        event(
                            session,
                            run,
                            Stage.ELIGIBILITY_EVALUATED,
                            outcome="simulated",
                            provider="fixture",
                            entity_id=opp.id,
                            refs=["demo/settlement_fixture.json"],
                        )
                    if live and settings.settlement_live_enabled:
                        try:
                            cases = await settlements.search(product)
                            for case in cases:
                                opp = persist_verified_settlement(session, entity, product, case)
                                ids.append(opp.id)
                                modes["settlement"] = "verified_public_sources"
                                event(
                                    session,
                                    run,
                                    Stage.ELIGIBILITY_EVALUATED,
                                    outcome=opp.payload["status"],
                                    provider=settlements.provider_name,
                                    entity_id=opp.id,
                                    refs=[e.url for e in case.evidence],
                                )
                        except ProviderUnavailable:
                            modes["settlement"] = "unavailable"
                            ids.extend(invalidate_settlements(session, entity.id))
                            warnings.append("Settlement primary sources unavailable; prior drafts disabled")
                event(session, run, Stage.AWAITING_USER_REVIEW)
        except TimeoutError:
            warnings.append("Run reached 90-second limit; review partial results")
        except Exception:  # noqa: BLE001 — worker boundary persists sanitized failures for polling clients.
            session.rollback()
            warnings.append("RUN_INTERRUPTED_OR_UNAVAILABLE")
        opportunities = session.scalars(select(Opportunity).where(Opportunity.id.in_(ids))).all()
        valid_ids = [o.id for o in opportunities if o.payload["status"] == "verified_match"]
        summary = {
            "products_scanned": len(products),
            "candidates": len(ids),
            "verified_matches": sum(o.payload["status"] == "verified_match" for o in opportunities),
            "rejected": sum(o.payload["status"] == "rejected" for o in opportunities),
            "needs_review": sum(o.payload["status"] == "needs_review" for o in opportunities),
            "simulated_settlements": sum(o.payload["simulated"] for o in opportunities),
            "prepared_packets": len(
                session.scalars(select(ClaimPacket).where(ClaimPacket.opportunity_id.in_(valid_ids))).all()
            ),
        }
        run.status = "partial" if warnings and ids else "failed" if warnings else "completed"
        run.payload = run.payload | {
            "summary": summary,
            "warnings": list(dict.fromkeys(warnings)),
            "provider_modes": modes,
            "opportunities": ids,
            "completed_at": now(),
        }
        session.commit()
        event(session, run, Stage.COMPLETED, outcome=run.status)
        if warnings:
            record_failure(settings.sentry_dsn, run.id)


def run_view(run):
    return view(run) | {"run_id": run.id, "status": run.status, "events_url": f"/api/runs/{run.id}/events"}
