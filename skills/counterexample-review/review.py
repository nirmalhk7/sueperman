"""Portable, offline reference checker. No network, tools, credentials or eligibility override."""

import json
import sys

FIELDS = {
    "official_source",
    "brand",
    "product_family",
    "model_number",
    "serial_prefix",
    "batch",
    "date_purchased",
    "region",
    "upc",
}


def review(conditions, source_refs):
    if (
        not isinstance(conditions, list)
        or len(conditions) > 20
        or source_refs not in [[], ["26-792"]]
    ):
        raise ValueError("Unsupported review input")
    if not source_refs:
        if conditions:
            raise ValueError("Conditions require a supplied citation")
        return [{"code": "no_candidate"}]
    seen, findings = set(), []
    for item in conditions:
        if not isinstance(item, dict) or set(item) != {"name", "status"}:
            raise ValueError("Unknown fields or instructions are not conditions")
        name, status = item["name"], item["status"]
        if (
            name not in FIELDS
            or name in seen
            or status not in {"true", "false", "unknown"}
        ):
            raise ValueError("Unsupported or duplicate condition")
        seen.add(name)
        if status != "true":
            findings.append(
                {
                    "code": "excluded_condition"
                    if status == "false"
                    else "unknown_condition",
                    "condition": name,
                    "source_ref": "26-792",
                }
            )
    if not conditions:
        raise ValueError("A supported candidate requires a checked condition list")
    return findings or [{"code": "checklist_exhausted", "source_ref": "26-792"}]


if __name__ == "__main__":
    payload = json.load(sys.stdin)
    if set(payload) != {"conditions", "source_refs"}:
        raise ValueError("Expected only conditions and source_refs")
    print(json.dumps(review(**payload)))
