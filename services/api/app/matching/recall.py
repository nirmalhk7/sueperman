from datetime import date

from app.matching.normalize import normalize_model, normalize_text
from app.p1.normalizers import additional_families
from app.schemas import Condition, MatchResult, ProductInput, RecallRecord
from app.security.source_policy import official_cpsc


def match_recall(product: ProductInput, recall: RecallRecord) -> MatchResult:
    conditions: list[Condition] = []

    def check(name, expected, observed, passed):
        conditions.append(
            Condition(
                name=name,
                expected=expected,
                observed=observed,
                status="unknown" if passed is None else "true" if passed else "false",
                source_id=recall.reference,
            )
        )

    trusted = official_cpsc(recall.official_url) and recall.source_type == "government"
    check("official_source", "CPSC HTTPS recall notice", recall.official_url, trusted)
    brand = normalize_text(product.brand)
    check("brand", recall.brand, product.brand, brand == normalize_text(recall.brand) if brand else None)
    family = normalize_text(recall.family).rstrip("s")
    families = (family, *additional_families(recall.reference, normalize_text(recall.brand), family))
    check(
        "product_family", list(families) if len(families) > 1 else recall.family, product.product_name,
        any(candidate in normalize_text(product.product_name) for candidate in families)
    )
    model = normalize_model(product.model_number)
    check(
        "model_number",
        recall.models,
        product.model_number,
        model in [normalize_model(m) for m in recall.models] if model and recall.models else None,
    )
    for restriction in recall.conditions:
        observed = getattr(product, restriction.name, None)
        passed = None
        if observed is not None:
            if isinstance(observed, date) and isinstance(restriction.expected, list):
                passed = (
                    date.fromisoformat(restriction.expected[0])
                    <= observed
                    <= date.fromisoformat(restriction.expected[1])
                )
                observed = observed.isoformat()
            elif restriction.name == "serial_prefix":
                passed = str(observed).startswith(str(restriction.expected))
            elif restriction.name in {"batch", "region", "upc"}:
                passed = normalize_model(str(observed)) == normalize_model(str(restriction.expected))
        check(restriction.name, restriction.expected, observed, passed)
    states = [c.status for c in conditions]
    # An untrusted record cannot prove exclusion either.
    status = (
        "needs_review"
        if not trusted or not recall.brand or not recall.family
        else "rejected"
        if "false" in states
        else "needs_review"
        if "unknown" in states
        else "verified_match"
    )
    reasons = [f"{c.name}: {c.status}" for c in conditions]
    if model and recall.models and conditions[3].status == "false":
        reasons.append("REJECTED — MODEL MISMATCH")
    return MatchResult(status=status, conditions=conditions, reasons=reasons, evidence_ids=[recall.reference])
