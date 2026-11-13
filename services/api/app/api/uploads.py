from pathlib import Path
from typing import Annotated

from fastapi import File, HTTPException, UploadFile
from sqlalchemy import select

from app.db import view
from app.models import (
    Product,
)
from app.providers.errors import ProviderUnavailable
from app.providers.gemini import GeminiReceiptExtractor
from app.providers.receipt import MAX_UPLOAD
from app.schemas import ImportResponse, ProductResponse


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
        if not settings.gemini_enabled or not settings.gemini_api_key:
            raise HTTPException(503, "Receipt extraction not configured; upload a UTF-8 CSV instead")
        try:
            extracted = await GeminiReceiptExtractor(settings.gemini_api_key, settings.gemini_model).extract(
                content, file.content_type
            )
        except ProviderUnavailable:
            raise HTTPException(503, "Receipt extraction unavailable; upload a UTF-8 CSV instead") from None
        with factory() as s:
            result = import_products(
                s, content, extracted=extracted, source_type="pdf" if extension == ".pdf" else "image"
            )
            result["parse_warnings"] = [
                "Scanned identifiers are unverified suggestions. Supply a confirmed CSV for exact matching."
            ]
            return result

    @app.get("/api/products", response_model=list[ProductResponse])
    def products():
        with factory() as s:
            return [
                view(p) | {"purchase_id": p.purchase_id, "demo": p.demo}
                for p in s.scalars(select(Product).order_by(Product.created_at))
            ]
