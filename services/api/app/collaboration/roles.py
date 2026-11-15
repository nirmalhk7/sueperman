"""Deterministic local replay roles. None executes a sponsor or claims model reasoning."""

import json

from app.config import ROOT
from app.matching.recall import match_recall
from app.schemas import Condition, MatchResult, ProductInput, RecallRecord

PRIORITY = ["model_number", "serial_prefix", "batch", "date_purchased", "region", "brand", "upc"]
RULE_VERSION = "26-792-v1"
OFFLINE_SKILL = {
    "identity": "local-counterexample-checklist",
    "version": 1,
    "checks": ["model_number", "serial_prefix", "batch", "date_purchased", "region"],
    "delivery": "repository; not Finch",
}


def load_recall():
    return RecallRecord(**json.loads((ROOT / "demo/recall_fixture.json").read_text()))


async def scout(product: ProductInput):
    from app.matching.normalize import normalize_model, normalize_text

    recall = load_recall()
    candidate = (
        normalize_text(product.brand) == normalize_text(recall.brand)
        or normalize_text(recall.family) in normalize_text(product.product_name)
        or normalize_model(product.model_number) in recall.models
    )
    return recall if candidate else None


def skeptic(product: ProductInput, recall):
    # Fixed checklist: match exact identifiers, evaluate only source-defined restrictions.
    result = match_recall(product, recall)
    if (
        recall.reference != "26-792"
        or recall.models != ["ZHX-PB22"]
        or recall.excerpt != "This recall involves NEWDERY power banks with model number ZHX-PB22."
    ):
        result.conditions.append(
            Condition(
                name="unsupported_source_conditions",
                expected="Manual review of changed official restrictions",
                source_id=recall.reference,
            )
        )
        result.status = "needs_review"
    return result


def public_facts(product: ProductInput, required=()):
    # Source-specific facts only. Never receipt/order/merchant or inferred suggestions.
    names = {"product_name", "brand", "model_number"} | (set(required) & set(PRIORITY))
    return {k: v for k, v in product.model_dump(mode="json").items() if k in names and v is not None}


def next_question(missing):
    return next((name for name in PRIORITY if name in missing), None)


def validate_review(review, expected: MatchResult, source_id):
    codes = {"true": "condition_passed", "false": "condition_failed", "unknown": "condition_unknown"}
    wanted = {(c.name, codes[c.status], source_id) for c in expected.conditions}
    actual = {(f.condition, f.code, f.source_ref) for f in review.findings}
    missing = [c.name for c in expected.conditions if c.status == "unknown"]
    status = "rejected" if expected.status == "rejected" else "needs_information" if missing else "completed"
    if (
        actual != wanted
        or len(review.findings) != len(wanted)
        or review.missing_conditions != missing
        or review.status != status
    ):
        raise ValueError("Agent challenge contradicts deterministic conditions")


def builder(product, recall, review):
    challenge = skeptic(product, recall)
    validate_review(review, challenge, recall.reference)
    false = [c for c in challenge.conditions if c.status == "false"]
    missing = [c.name for c in challenge.conditions if c.status == "unknown"]
    question = next_question(missing) if challenge.status == "needs_review" else None
    model_failed = next((c for c in false if c.name == "model_number"), None)
    explanation = (
        f"Model {product.model_number} differs from official affected model(s): {', '.join(recall.models)}."
        if model_failed
        else "Supported exclusion: " + ", ".join(c.name for c in false)
        if false
        else "Unresolved source condition: " + ", ".join(missing)
        if missing
        else "No additional supported exclusion found in model, batch, date or region checks."
    )
    return {
        "finding": f"Scout proposed recall {recall.reference} from recorded CPSC evidence.",
        "challenge": explanation,
        "missing_information": missing,
        "question_field": question,
        "question": f"What is the {question.replace('_', ' ')} printed on your product or record?"
        if question
        else None,
        "decision": challenge.status,
        "conditions": [c.model_dump(mode="json") for c in challenge.conditions],
    }
