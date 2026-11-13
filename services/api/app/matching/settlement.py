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


def match_verified_settlement(product, rules, today: date) -> MatchResult:
    """Missing personal/legal facts remain unknown; a purchase never implies an attestation."""
    checks = [
        Condition(
            name="merchant",
            expected="Kroger",
            observed=product.merchant,
            status="true" if normalize_text(product.merchant) == "kroger" else "false",
            source_id=rules.official_url,
        ),
        Condition(
            name="purchase_window",
            expected=[rules.start.isoformat(), rules.end.isoformat()],
            observed=product.date_purchased.isoformat() if product.date_purchased else None,
            status="unknown"
            if not product.date_purchased
            else "true"
            if rules.start <= product.date_purchased <= rules.end
            else "false",
            source_id=rules.evidence[2].url,
        ),
        Condition(
            name="open_deadline",
            expected=rules.deadline.isoformat(),
            observed=today.isoformat(),
            status="true" if today <= rules.deadline else "false",
            source_id=rules.evidence[2].url,
        ),
        *[
            Condition(name=name, expected=expected, source_id=rules.evidence[2].url)
            for name, expected in [
                ("qualifying_product", "One or more prescription drugs; verify actual transaction"),
                ("insured_payment", "Paid in whole or part using insurance"),
                ("us_or_territories", "Individual in the United States or its territories"),
                (
                    "class_exclusions",
                    "No applicable judicial/Kroger officer/director/opt-out/prior litigation exclusions",
                ),
                (
                    "proof_requirements",
                    "Administrator claimant status and documentation requirements must be checked",
                ),
            ]
        ],
    ]
    outcome = (
        "expired"
        if today > rules.deadline
        else "ineligible"
        if any(c.status == "false" for c in checks)
        else "uncertain"
    )
    return MatchResult(
        status=outcome,
        conditions=checks,
        reasons=["Verified open case; personal eligibility and proof remain unconfirmed. Preparation only."],
        evidence_ids=[e.url for e in rules.evidence],
    )
