"""Public read-only live proof using production adapter; no sponsor credentials required."""

import asyncio
import json
from pathlib import Path

from app.matching.recall import match_recall
from app.providers.cpsc import CPSCRecallSource
from app.schemas import ProductInput


async def main():
    product = ProductInput(
        product_name="Portable Power Bank", brand="NEWDERY", model_number="ZHX-PB22"
    )
    records = await CPSCRecallSource().search(product)
    assert len(records) == 1
    recall = records[0]
    exact = match_recall(product, recall)
    product.model_number = "ZHX-PB23"
    negative = match_recall(product, recall)
    assert exact.status == "verified_match"
    assert negative.status == "rejected"
    result = {
        "provider": "cpsc",
        "mode": recall.mode,
        "url": recall.official_url,
        "fetched_at": recall.fetched_at.isoformat(),
        "reference": recall.reference,
        "exact_status": exact.status,
        "near_match_status": negative.status,
        "affected_models": recall.models,
        "record_count": len(records),
    }
    output = Path("docs/evidence/live-cpsc.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(output.read_text())


if __name__ == "__main__":
    asyncio.run(main())
