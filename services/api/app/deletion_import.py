"""Require fresh, file-specific consent before recreating deleted purchases."""

import hashlib

from fastapi.responses import JSONResponse

from app import deletion


def import_fingerprint(source_type, content):
    digest = hashlib.sha256(content).hexdigest()
    return hashlib.sha256(f"{source_type}:{digest}".encode()).hexdigest()


def check_import(app, source_type, content, confirmation):
    """Return (error response, was previously deleted), without model calls.

    Call again while holding the SQLite write transaction after an asynchronous
    extraction: deletion may have happened while the provider was responding.
    """
    runtime = getattr(app.state, "deletion_runtime", None)
    if runtime is None or runtime.path is None:
        return None, False
    try:
        challenge = deletion.reimport_challenge(
            runtime.path, import_fingerprint(source_type, content), expected_lineage=runtime.lineage)
    except deletion.DeletionJournalError:
        return JSONResponse(status_code=503, content={
            "code": "DELETION_HISTORY_UNAVAILABLE",
            "message": "Deletion history unavailable; restore it before importing purchases."}), False
    if challenge and confirmation != challenge:
        return JSONResponse(status_code=409, content={
            "code": "REIMPORT_CONFIRMATION_REQUIRED",
            "message": "Purchases from this file were deleted. Confirm a fresh import to recreate them. "
                       "Receipts will be read again and normal usage limits apply.",
            "reimport_token": challenge}), True
    return None, challenge is not None


class ReceiptAlignmentError(ValueError):
    """Remaining rows cannot safely identify the newly extracted receipt items."""


def receipt_row_indices(remaining, extracted):
    """Retain survivor identities even when a provider changes extraction order.

    Compare original immutable extraction facts, not the current user-corrected
    Product. Without a unique full match, do not guess which purchase survived.
    """
    if not remaining:
        return None
    message = ("Receipt items could not be matched safely to the remaining purchases. "
               "Review the receipt and upload a CSV containing only the purchases you want to add.")
    count = remaining[0].payload.get("import_count")
    if type(count) is not int or not 1 <= count <= 100 or len(extracted) != count:
        raise ReceiptAlignmentError(message)
    facts = [row.model_dump(mode="json") for row in extracted]
    assigned: list[int | None] = [None] * len(extracted)
    used = set()
    for purchase in remaining:
        original = purchase.payload.get("import_facts")
        index = purchase.import_key.rsplit(":", 1)[-1]
        if (purchase.payload.get("import_count") != count or not isinstance(original, dict)
                or not index.isdecimal() or str(int(index)) != index
                or not 0 <= int(index) < count or int(index) in used):
            raise ReceiptAlignmentError(message)
        matches = [position for position, extracted_facts in enumerate(facts) if extracted_facts == original]
        if len(matches) != 1 or assigned[matches[0]] is not None:
            raise ReceiptAlignmentError(message)
        assigned[matches[0]] = int(index)
        used.add(int(index))
    available = iter(index for index in range(count) if index not in used)
    return [index if index is not None else next(available) for index in assigned]
