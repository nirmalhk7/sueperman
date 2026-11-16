"""Local-only configuration and exact synthetic admission; no provider calls."""

import hashlib
import json
import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import select

from app.config import ROOT
from app.models import Product, Purchase
from app.providers.receipt import FixtureReceiptExtractor
from app.schemas import ProductInput


def credentials(settings):
    if not (settings.diwali_enabled and settings.diwali_operator_demo
            and settings.diwali_live_authorized and settings.band_enabled):
        raise ValueError("Bounded operator BAND session is disabled")
    if settings.agent37_enabled:
        raise ValueError("Agent37 case snapshot integration is not verified")
    if settings.lyzr_enabled and (not settings.lyzr_api_key or not settings.lyzr_review_agent_id
                                  or settings.diwali_max_lyzr_calls_per_run == 0):
        raise ValueError("Bounded Lyzr reviewer profile is unavailable")
    if settings.finch_enabled:
        if not settings.lyzr_enabled:
            raise ValueError("Finch procedural skill requires the configured reviewer")
        from app.diwali.finch_skill import load_configured_skill
        load_configured_skill(settings)
    if settings.band_credentials_file:
        path = Path(settings.band_credentials_file)
        if path.stat().st_mode & 0o077 or path.stat().st_size > 65536:
            raise ValueError("BAND credential file must be private and bounded")
        return json.loads(path.read_text())
    values = dotenv_values(ROOT / ".env") | dict(os.environ)
    names = {"manager": "CONTROLLER", "researcher": "SCOUT", "skeptic": "SKEPTIC", "builder": "BUILDER"}
    return {"room_id": values.get("BAND_ROOM_ID"), "actors": {
        role: {"agent_id": values.get(f"BAND_{prefix}_AGENT_ID"), "api_key": values.get(f"BAND_{prefix}_API_KEY")}
        for role, prefix in names.items()}}


def validate_synthetic(session, purchase_ids):
    baseline = json.loads((ROOT / "harness/diwali/baseline.json").read_text())
    for name in ("demo/orders.csv", "demo/recall_fixture.json", "demo/settlement_fixture.json"):
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != baseline["fixture_digests"][name]:
            raise ValueError("Synthetic fixture bytes changed")
    allowed = [item.model_dump(mode="json") for item in
               FixtureReceiptExtractor().extract((ROOT / "demo/orders.csv").read_bytes())]
    for identifier in purchase_ids:
        purchase = session.get(Purchase, identifier)
        product = session.scalar(select(Product).where(Product.purchase_id == identifier))
        if (purchase is None or product is None or not purchase.demo or not product.demo
                or ProductInput.model_validate(product.payload["product"]).model_dump(mode="json") not in allowed):
            raise ValueError("BAND accepts exact synthetic fixture content only")
