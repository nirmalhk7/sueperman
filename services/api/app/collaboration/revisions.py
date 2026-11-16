"""Material revisions revoke local review before any packet can be exported."""

import hashlib
from pathlib import Path

from sqlalchemy import select

from app.collaboration.ledger import LOCAL_SKILL_HASH, RULE_VERSION, current, digest, revision_for
from app.config import ROOT
from app.models import CollaborationEvidence, Opportunity, Product


def primary_record(s, product_id):
    return s.scalar(
        select(Opportunity).where(
            Opportunity.product_id == product_id,
            Opportunity.kind == "recall",
            Opportunity.source_id == "26-792",
        )
    )


def source_binding(s, product_id):
    record = primary_record(s, product_id)
    return digest(record.payload.get("recall")) if record else None


def latest_live_hash(s, source_ref):
    # Official notice revisions affect every product citing that notice.
    rows = s.scalars(
        select(CollaborationEvidence)
        .where(CollaborationEvidence.source_ref == source_ref)
        .order_by(CollaborationEvidence.created_at.desc())
    )
    return next(
        (
            r.payload["content_sha256"]
            for r in rows
            if r.payload.get("mode") == "live" and "content_sha256" in r.payload
        ),
        None,
    )


def fixture_binding():
    return digest((ROOT / "demo/recall_fixture.json").read_text())


def invalid_reason(s, case, row):
    if not row:
        return "Case revision unavailable"
    product = s.get(Product, case.product_id)
    data = row.payload
    if not product or data["original_product_hash"] != digest(product.payload["product"]):
        return "Product changed; start a new investigation"
    expected_skill = LOCAL_SKILL_HASH
    if case.payload["mode"] == "live":
        try:
            expected_skill = hashlib.sha256(Path(data["skill_package_path"]).read_bytes()).hexdigest()
        except (OSError, TypeError, KeyError):
            return "Pinned skill package unavailable; start a new investigation"
        if any(latest_live_hash(s, e["id"]) != e["content_sha256"] for e in data["evidence"]):
            return "New live evidence changed; start a new investigation"
    if data["rule_version"] != RULE_VERSION or data["skill_hash"] != expected_skill:
        return "Rules or skill changed; start a new investigation"
    if (
        revision_for(data["facts"], data["evidence"], skill_hash=expected_skill) != case.current_revision
        or data.get("source_binding") != source_binding(s, case.product_id)
        or data.get("fixture_binding") != fixture_binding()
    ):
        return "Evidence changed; start a new investigation"
    return None


def revoke_if_changed(s, case):
    row = current(s, case)
    if not row:
        return None
    reason = invalid_reason(s, case, row)
    if reason:
        row.payload = row.payload | {"approval": None}
        case.status = "partial"
        case.payload = case.payload | {"warnings": [reason]}
        s.commit()
    return reason
