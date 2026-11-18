import hashlib
from pathlib import Path
from typing import Annotated

from fastapi import File, Form, HTTPException, UploadFile
from sqlalchemy import select

from app.db import view
from app.deletion_import import ReceiptAlignmentError, check_import, receipt_row_indices
from app.models import (
    AgentRun,
    CaseRecord,
    ClaimPacket,
    CollaborationRun,
    Opportunity,
    Product,
    Purchase,
    now,
)
from app.providers.errors import ProviderUnavailable
from app.providers.gemini import GeminiReceiptExtractor
from app.providers.openai_receipt import OpenAIReceiptExtractor, reserve_receipt_call
from app.providers.receipt import MAX_UPLOAD
from app.schemas import (
    IdentifierConfirmation,
    ImportResponse,
    ProductInput,
    ProductResponse,
    PurchaseCorrection,
)


def register(app, factory, settings, import_products):
    @app.post("/api/uploads/purchases", response_model=ImportResponse)
    async def upload(file: Annotated[UploadFile, File()],
                     reimport_confirmation: Annotated[str | None, Form(max_length=64)] = None):
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
                    s.connection().exec_driver_sql("BEGIN IMMEDIATE")
                    error, _deleted = check_import(app, "csv", content, reimport_confirmation)
                    if error is not None:
                        return error
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
            s.connection().exec_driver_sql("BEGIN IMMEDIATE")
            error, previously_deleted = check_import(app, source_type, content, reimport_confirmation)
            if error is not None:
                return error
            existing = s.scalars(
                select(Purchase).where(Purchase.import_key.like(f"{source_type}:{digest}:%"))
            ).all()
            if existing and not previously_deleted:
                ids = [p.id for p in existing]
                return {
                    "purchase_ids": ids,
                    "product_ids": [
                        p.id for p in s.scalars(select(Product).where(Product.purchase_id.in_(ids), Product.payload["superseded"].as_boolean().is_not(True)))
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
            s.connection().exec_driver_sql("BEGIN IMMEDIATE")
            error, previously_deleted = check_import(app, source_type, content, reimport_confirmation)
            if error is not None:
                return error
            row_indices = None
            if previously_deleted:
                remaining = s.scalars(select(Purchase).where(
                    Purchase.import_key.like(f"{source_type}:{digest}:%"))).all()
                try:
                    row_indices = receipt_row_indices(remaining, extracted)
                except ReceiptAlignmentError as exc:
                    raise HTTPException(409, str(exc)) from None
            result = import_products(s, content, extracted=extracted, source_type=source_type,
                                     row_indices=row_indices)
            result["parse_warnings"] = [
                "Scanned identifiers are unverified suggestions. Review and confirm them before checking purchases."
            ]
            if previously_deleted:
                result["parse_warnings"].append(
                    "Fresh re-import confirmed. Receipt read again; normal usage limits apply, "
                    "including repeated confirmed uploads of a previously deleted receipt.")
            return result

    @app.post("/api/products/{identifier}/confirm-identifiers", response_model=ProductResponse)
    def confirm_identifiers(identifier: str, body: IdentifierConfirmation):
        with factory() as s:
            product = s.get(Product, identifier)
            if product is None:
                raise HTTPException(404, "Product not found")
            if product.payload.get("superseded"):
                raise HTTPException(409, "Purchase corrected; use the current revision")
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

    @app.post("/api/products/{identifier}/corrections", response_model=ProductResponse)
    def correct_purchase(identifier: str, body: PurchaseCorrection):
        with factory() as s:
            s.connection().exec_driver_sql("BEGIN IMMEDIATE")
            original = s.get(Product, identifier)
            if original is None:
                raise HTTPException(404, "Product not found")
            updates = body.model_dump(exclude_unset=True, exclude={"confirmed"})
            updates["model_number"] = body.model_number.strip()
            if not updates["model_number"]:
                raise HTTPException(422, "Model number cannot be blank")
            if updates.get("brand"):
                updates["brand"] = updates["brand"].strip() or None
            facts = ProductInput(**original.payload["product"]).model_copy(
                update=updates | {"user_confirmed_identifiers": True})
            if original.payload.get("superseded"):
                replacement = s.get(Product, original.payload["replaced_by"])
                if replacement.payload["product"] == facts.model_dump(mode="json") and not replacement.payload.get("superseded"):
                    return view(replacement) | {"purchase_id": replacement.purchase_id}
                raise HTTPException(409, "Purchase changed; reload before correcting")
            active = s.scalars(select(AgentRun).where(AgentRun.status.in_(["queued", "running"])))
            team_active = s.scalar(select(CollaborationRun).join(
                CaseRecord, CollaborationRun.case_id == CaseRecord.id).where(
                    CaseRecord.product_id == original.id,
                    CollaborationRun.status.in_(["queued", "investigating", "challenging", "building"])))
            if team_active or any(original.purchase_id in run.payload["purchase_ids"] for run in active):
                raise HTTPException(409, "Investigation active; wait before correcting")
            if original.payload["product"] == facts.model_dump(mode="json"):
                return view(original) | {"purchase_id": original.purchase_id}
            replacement = Product(purchase_id=original.purchase_id, demo=original.demo,
                model_number=facts.model_number, upc=facts.upc,
                payload=original.payload | {"product": facts.model_dump(mode="json"),
                    "revision": original.payload.get("revision", 1) + 1,
                    "previous_product_id": original.id, "corrected_at": now()})
            s.add(replacement)
            s.flush()
            original.payload = original.payload | {"superseded": True, "replaced_by": replacement.id}
            for opportunity in s.scalars(select(Opportunity).where(Opportunity.product_id == original.id)):
                opportunity.payload = opportunity.payload | {"stale": True}
                for packet in s.scalars(select(ClaimPacket).where(ClaimPacket.opportunity_id == opportunity.id)):
                    packet.payload = packet.payload | {"stale": True, "status": "needs_evidence", "approved_at": None}
            s.commit()
            return view(replacement) | {"purchase_id": replacement.purchase_id}

    @app.get("/api/products", response_model=list[ProductResponse])
    def products():
        with factory() as s:
            return [
                view(p) | {"purchase_id": p.purchase_id, "demo": p.demo}
                for p in s.scalars(select(Product).where(Product.payload["superseded"].as_boolean().is_not(True)).order_by(Product.created_at))
            ]
