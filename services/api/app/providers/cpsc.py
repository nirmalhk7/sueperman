import json
from datetime import UTC

from app.config import ROOT
from app.matching.normalize import normalize_model, normalize_text
from app.schemas import ProductInput, RecallRecord, RemedyKind


class FixtureRecallSource:
    provider_name = "cpsc_recording"
    mode = "replay"

    async def search(self, product: ProductInput) -> list[RecallRecord]:
        r = RecallRecord(**json.loads((ROOT / "demo/recall_fixture.json").read_text()))
        candidate = (
            normalize_text(product.brand) == normalize_text(r.brand)
            or normalize_text(r.family) in normalize_text(product.product_name)
            or normalize_model(product.model_number) in [normalize_model(m) for m in r.models]
        )
        return [r] if candidate else []


class CPSCRecallSource:
    """Official REST lookup; only an explicitly supported notice can pass hard gates.

    General CPSC prose is not a model-list or restriction schema. Unknown notices
    remain manual review until a source-specific normalizer is tested.
    """

    provider_name = "cpsc"
    mode = "live"

    def __init__(self, client=None, cache_dir=None, *, reviewed_notices=False):
        self.client = client
        self.reviewed_notices = reviewed_notices
        self.cache_dir = cache_dir or ROOT / "uploads/cpsc-cache"
        self._cache = {}
        self.truncated = False

    async def search(self, product: ProductInput) -> list[RecallRecord]:
        import httpx

        query = product.brand or product.product_name
        if query in self._cache:
            self.truncated = len(self._cache[query]) > 10
            return self._cache[query][:10]
        if self.client is None:
            async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                records = await self._fetch(client, query)
        else:
            records = await self._fetch(self.client, query)
        self._cache[query] = records
        self.truncated = len(records) > 10
        return records[:10]

    async def _fetch(self, client, query):
        import asyncio
        import hashlib
        import random
        import re
        from datetime import datetime

        import httpx
        from pydantic import ValidationError

        from app.providers.errors import ProviderUnavailable
        from app.schemas import Condition
        from app.security.source_policy import official_cpsc

        try:
            for attempt in range(2):
                response = await client.get(
                    "https://www.saferproducts.gov/RestWebServices/Recall",
                    params={"ProductName": query, "format": "json"},
                    timeout=8,
                    follow_redirects=False,
                )
                if (response.status_code == 429 or response.status_code >= 500) and attempt == 0:
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                    continue
                response.raise_for_status()
                break
            data = response.json()
            if not isinstance(data, list):
                raise TypeError("Unsupported CPSC schema")
            fetched_at = datetime.now(UTC)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_key = hashlib.sha256(query.encode()).hexdigest()
            (self.cache_dir / f"{cache_key}.json").write_text(
                json.dumps({"fetched_at": fetched_at.isoformat(), "response": data})
            )
            records = []
            seen: dict[str, dict] = {}
            for row in data:
                if "RecallID" not in row:
                    raise ValueError("Missing CPSC identity")
                identity = row["RecallNumber"]
                if identity in seen:
                    if seen[identity] != row:
                        raise ValueError("Conflicting official records for one recall")
                    continue
                seen[identity] = row
                url, description = row["URL"], row["Description"]
                if not official_cpsc(url):
                    raise ValueError("Untrusted CPSC citation")
                if self.reviewed_notices:
                    from app.p1.normalizers import normalize_reviewed

                    reviewed = normalize_reviewed(row, fetched_at)
                    if reviewed is not None:
                        records.append(reviewed)
                        continue
                number = row["RecallNumber"]
                reference = number[:2] + "-" + number[2:]
                supported = (
                    number == "26792"
                    and "NEWDERY" in row["Title"]
                    and "This recall involves NEWDERY power banks with model number ZHX-PB22." in description
                )
                # Any change in the published affected-product description requires review.
                expected_description = (
                    "This recall involves NEWDERY power banks with model number ZHX-PB22. "
                    "The power banks are black with yellow cables. The brand name “NEWDERY” is engraved on "
                    "the front and the model number “ZHX-PB22” is printed on the back."
                )
                conditions = (
                    []
                    if supported and description == expected_description
                    else [
                        Condition(
                            name="unsupported_source_conditions",
                            expected="Manual review of full official notice",
                        )
                    ]
                )
                remedy_text = "\n".join(r["Name"] for r in row.get("Remedies", []))
                options = {r["Option"].casefold() for r in row.get("RemedyOptions", [])}
                known_remedies: list[RemedyKind] = ["refund", "repair", "replacement", "credit"]
                remedy: RemedyKind = next((x for x in known_remedies if x in options), "unknown")
                contact = (
                    re.search(
                        r"https://www\.newdery\.com/pages/newdery-power-bank-recalls",
                        row.get("ConsumerContact", ""),
                    )
                    if supported
                    else None
                )
                records.append(
                    RecallRecord(
                        reference=reference,
                        title=row["Title"],
                        brand="NEWDERY" if supported else "",
                        family="power bank" if supported else "",
                        models=["ZHX-PB22"] if supported else [],
                        official_url=url,
                        fetched_at=fetched_at,
                        publisher="U.S. Consumer Product Safety Commission",
                        source_type="government",
                        excerpt=description,
                        remedy_kind=remedy,
                        instructions=remedy_text or "Remedy unknown; consult official notice.",
                        safety_instructions=remedy_text or None,
                        contact_url=contact.group(0) if contact else None,
                        required_documents=[
                            "Photo showing model, serial number and official required markings",
                            "User confirmation of lawful disposal (never prefilled)",
                        ]
                        if supported
                        else [],
                        conditions=conditions,
                        mode="live",
                    )
                )
            return records
        except (httpx.HTTPError, ValueError, KeyError, TypeError, ValidationError, OSError) as exc:
            raise ProviderUnavailable("CPSC unavailable or unsupported response") from exc
