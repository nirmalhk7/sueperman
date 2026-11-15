"""Reviewed notice mappings, bound to the entire observed official API record.

No prose/model extraction: any upstream change requires a fresh human review.
Published remedy amounts are instructions, never a promised personal payout.
"""

import hashlib
import json
from pathlib import Path
from types import MappingProxyType

from app.schemas import RecallRecord

# Freeze reviewed public product-family wording at import, not inside a matcher/reducer.
_families = MappingProxyType({
    (pin["number"][:2] + "-" + pin["number"][2:], pin["brand"].casefold(), pin["family"]):
        tuple(pin.get("family_aliases", ()))
    for pin in json.loads(Path(__file__).with_name("normalizers.json").read_text())["notices"]
})


def additional_families(reference, brand, family):
    return _families.get((reference, brand, family), ())


def normalize_reviewed(row, fetched_at):
    catalog = json.loads(Path(__file__).with_name("normalizers.json").read_text())
    pin = next((p for p in catalog["notices"] if p["number"] == row.get("RecallNumber")), None)
    actual = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if pin is None or actual != pin["raw_sha256"] or row.get("URL") != pin["official_url"]:
        return None
    instructions = "\n".join(item["Name"] for item in row["Remedies"])
    number = pin["number"]
    return RecallRecord(
        reference=number[:2] + "-" + number[2:], title=row["Title"], brand=pin["brand"],
        family=pin["family"], models=pin["models"], official_url=pin["official_url"],
        fetched_at=fetched_at, source_type="government", publisher="U.S. Consumer Product Safety Commission",
        excerpt=row["Description"], remedy_kind="refund", instructions=instructions,
        safety_instructions=instructions, contact_url=pin["contact_url"],
        required_documents=pin["required_documents"], conditions=[], mode="live",
    )
