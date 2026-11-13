from app.schemas import ProductInput, RecallRecord


def compose(product: ProductInput, recall: RecallRecord) -> dict:
    fields = {
        k: v
        for k, v in product.model_dump(mode="json").items()
        if k in {"product_name", "brand", "model_number", "date_purchased", "merchant"} and v is not None
    }
    lines = [
        "# Recall remedy draft",
        "",
        "Local draft only; not an external submission.",
        "Verify official terms and submit requests yourself. No refund is guaranteed.",
        f"\n## Verified product facts\n{fields}",
        f"\n## Official instructions\n{recall.instructions}",
        f"\n## Safety\n{recall.safety_instructions or 'Consult the official notice.'}",
        "\n## Missing evidence — user must provide",
        *[f"- [ ] {d}" for d in recall.required_documents],
        "\nNo user declarations, signature, name, serial number or disposal attestation supplied.",
        f"\nSource: {recall.official_url}",
        f"Observed: {recall.fetched_at.isoformat()}",
        f"Mode: {'OFFLINE REPLAY of a real published recall' if recall.mode == 'replay' else 'LIVE CPSC lookup'}",
    ]
    return {
        "version": 1,
        "status": "ready_for_review",
        "contact_or_portal_url": recall.contact_url,
        "instructions": recall.instructions,
        "safety_instructions": recall.safety_instructions,
        "completed_fields": fields,
        "required_documents": recall.required_documents,
        "missing_documents": recall.required_documents,
        "user_declaration_required": True,
        "markdown": "\n".join(lines),
        "generated_at": None,
        "approved_at": None,
        "reviewed_at": None,
        "mode": recall.mode,
    }
