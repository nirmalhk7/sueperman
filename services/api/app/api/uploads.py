import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import File, HTTPException, UploadFile
from sqlalchemy import select

from app.db import view
from app.models import (
    AgentRun,
    Opportunity,
    Product,
    Purchase,
)
from app.providers.errors import ProviderUnavailable
from app.providers.gemini import GeminiReceiptExtractor
from app.providers.openai_receipt import OpenAIReceiptExtractor, reserve_receipt_call
from app.providers.receipt import MAX_UPLOAD
from app.schemas import IdentifierConfirmation, ImportResponse, ProductInput, ProductResponse


def register(app, factory, settings, import_products):
    @app.post("/api/uploads/purchases", response_model=ImportResponse)
    async def upload(file: Annotated[UploadFile, File()]):
        extension = Path(file.filename or "").suffix.lower()
        content = await file.read(MAX_UPLOAD + 1)
        await file.close()
        if len(content) > MAX_UPLOAD:
            raise HTTPException(422, "Upload exceeds 10MB")
        if extension == ".csv" and file.content_type in {
            "text/csv",
            "application/csv",
            "application/vnd.ms-excel",
            "text/plain",
        }:
            try:
                with factory() as s:
                    return import_products(s, content)
            except ValueError:
                raise HTTPException(422, "Invalid CSV; product_name and valid dates required") from None
        allowed = {
            ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
            ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
            ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
            ".pdf": ("application/pdf", b"%PDF-"),
        }
        if extension not in allowed or file.content_type != allowed[extension][0]:
            raise HTTPException(422, "Unsupported receipt type; use CSV, PNG, JPEG or PDF")
        if not content.startswith(allowed[extension][1]):
            raise HTTPException(422, "File content does not match its receipt type")
        source_type = "pdf" if extension == ".pdf" else "image"
        digest = hashlib.sha256(content).hexdigest()
        with factory() as s:
            existing = s.scalars(
                select(Purchase).where(Purchase.import_key.like(f"{source_type}:{digest}:%"))
            ).all()
            if existing:
                ids = [p.id for p in existing]
                return {
                    "purchase_ids": ids,
                    "product_ids": [
                        p.id for p in s.scalars(select(Product).where(Product.purchase_id.in_(ids)))
                    ],
                    "parse_warnings": ["Existing receipt import reused; no additional model request."],
                }
        use_openai = source_type == "image" and settings.openai_receipt_enabled
        if use_openai:
            if not settings.openai_api_key:
                raise HTTPException(503, "Photo reading not configured; upload a UTF-8 CSV instead")
            if not reserve_receipt_call(factory, settings.openai_receipt_daily_limit):
                raise HTTPException(429, "Daily receipt-photo limit reached; try tomorrow or upload CSV")
        elif not settings.gemini_enabled or not settings.gemini_api_key:
            raise HTTPException(503, "Receipt extraction not configured; upload a UTF-8 CSV instead")
        try:
            if use_openai:
                extracted = await OpenAIReceiptExtractor(
                    settings.openai_api_key, settings.openai_receipt_model
                ).extract(content, file.content_type)
            else:
                extracted = await GeminiReceiptExtractor(settings.gemini_api_key, settings.gemini_model).extract(
                    content, file.content_type
                )
        except ProviderUnavailable:
            raise HTTPException(503, "Receipt extraction unavailable; upload a UTF-8 CSV instead") from None
        with factory() as s:
            result = import_products(s, content, extracted=extracted, source_type=source_type)
            result["parse_warnings"] = [
                "Scanned identifiers are unverified suggestions. Review and confirm them before checking purchases."
            ]
            return result

    @app.post("/api/products/{identifier}/confirm-identifiers", response_model=ProductResponse)
    def confirm_identifiers(identifier: str, body: IdentifierConfirmation):
        with factory() as s:
            product = s.get(Product, identifier)
            if product is None:
                raise HTTPException(404, "Product not found")
            if product.payload.get("source_type") not in {"image", "pdf"}:
                raise HTTPException(409, "Only extracted receipts require identifier confirmation")
            active = s.scalars(select(AgentRun).where(AgentRun.status.in_(["queued", "running"]))).all()
            if s.scalar(select(Opportunity).where(Opportunity.product_id == identifier)) or any(
                product.purchase_id in run.payload["purchase_ids"] for run in active
            ):
                raise HTTPException(
                    409, "This purchase has already been checked; import a corrected record instead"
                )
            facts = ProductInput(**product.payload["product"]).model_copy(
                update={
                    "model_number": body.model_number.strip(),
                    "brand": body.brand.strip() or None if body.brand else None,
                    "upc": body.upc,
                    "user_confirmed_identifiers": True,
                }
            )
            if not facts.model_number:
                raise HTTPException(422, "Model number cannot be blank")
            product.model_number, product.upc = facts.model_number, facts.upc
            product.payload = product.payload | {"product": facts.model_dump(mode="json")}
            s.commit()
            return view(product) | {"purchase_id": product.purchase_id}

    @app.get("/api/products", response_model=list[ProductResponse])
    def products():
        with factory() as s:
            return [
                view(p) | {"purchase_id": p.purchase_id, "demo": p.demo}
                for p in s.scalars(select(Product).order_by(Product.created_at))
            ]
