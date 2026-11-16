"""Pinned Agent37 entry point: only the supported public CPSC lookup, no user input."""

import asyncio
import json
import tempfile
from pathlib import Path

from app.providers.cpsc import CPSCRecallSource
from app.schemas import ProductInput


async def main():
    with tempfile.TemporaryDirectory(prefix="sueperman-scout-") as directory:
        async with asyncio.timeout(75):
            records = await CPSCRecallSource(cache_dir=Path(directory)).search(
                ProductInput(product_name="Power Bank", brand="NEWDERY")
            )
            print(json.dumps([r.model_dump(mode="json") for r in records if r.reference == "26-792"]))


if __name__ == "__main__":
    asyncio.run(main())
