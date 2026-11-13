from sqlalchemy import select

from app.agent.orchestrator import event
from app.db import view
from app.matching.recall import match_recall
from app.models import (
    AgentRun,
    EligibilityAssessment,
    Opportunity,
    Product,
    SourceEvidence,
)
from app.schemas import DetailResponse, OpportunityResponse, ProductInput, RecallRecord


def register(app, factory, get):
    @app.get("/api/opportunities", response_model=list[OpportunityResponse])
    def opportunities(run_id: str | None = None):
        with factory() as s:
            query = select(Opportunity)
            if run_id:
                run = get(s, AgentRun, run_id)
                query = query.where(Opportunity.id.in_(run.payload.get("opportunities", [])))
            return [
                view(o) | {"purchase_model": get(s, Product, o.product_id).model_number}
                for o in s.scalars(query)
            ]

    @app.get("/api/opportunities/{identifier}", response_model=DetailResponse)
    def opportunity_detail(identifier: str):
        with factory() as s:
            o = get(s, Opportunity, identifier)
            return view(o) | {
                "product": view(get(s, Product, o.product_id)),
                "evidence": [
                    view(e)
                    for e in s.scalars(select(SourceEvidence).where(SourceEvidence.opportunity_id == o.id))
                ],
                "assessment": view(
                    s.scalar(
                        select(EligibilityAssessment).where(EligibilityAssessment.opportunity_id == o.id)
                    )
                ),
            }

    @app.post("/api/opportunities/{identifier}/recheck")
    def recheck(identifier: str):
        with factory() as s:
            o = get(s, Opportunity, identifier)
            result = None
            if o.kind == "recall":
                result = match_recall(
                    ProductInput(**get(s, Product, o.product_id).payload["product"]),
                    RecallRecord(**o.payload["recall"]),
                )
            runs = s.scalars(select(AgentRun).order_by(AgentRun.created_at.desc())).all()
            run = next((r for r in runs if o.id in r.payload.get("opportunities", [])), None)
            if run:
                event(s, run, "RECHECK", refs=[o.source_id])
            return {"status": result.status if result else o.payload["status"], "non_mutating": True}
