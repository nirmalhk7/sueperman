from datetime import date

from app.matching.normalize import normalize_model, normalize_text
from app.schemas import Condition, MatchResult, ProductInput, SettlementRecord


def match_settlement(product: ProductInput, rules: SettlementRecord, today: date) -> MatchResult:
    known_date = product.date_purchased
    checks = [
        Condition(
            name="qualifying_product",
            expected=rules.model,
            observed=product.model_number,
            status="true"
            if normalize_model(product.model_number) == normalize_model(rules.model)
            and normalize_text(product.brand) == normalize_text(rules.brand)
            else "false",
        ),
        Condition(
            name="purchase_window",
            expected=[rules.start.isoformat(), rules.end.isoformat()],
            observed=known_date.isoformat() if known_date else None,
            status="unknown"
            if not known_date
            else "true"
            if rules.start <= known_date <= rules.end
            else "false",
        ),
        Condition(
            name="open_deadline",
            expected=rules.deadline.isoformat(),
            observed=today.isoformat(),
            status="true" if today <= rules.deadline else "false",
        ),
    ]
    status = (
        "ineligible"
        if any(c.status == "false" for c in checks)
        else "uncertain"
        if not known_date
        else "eligible_candidate"
    )
    return MatchResult(
        status=status,
        conditions=checks,
        reasons=["SIMULATED CASE — NO REAL CLAIM AVAILABLE", "Receipt required; user must verify proof."],
        evidence_ids=[rules.source_url],
    )
