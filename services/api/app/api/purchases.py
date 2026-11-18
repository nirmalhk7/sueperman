"""Explicit purchase deletion with a fresh, separately confirmed shared scope."""

from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from app.deletion_lifecycle import DeletionConflict, PurchaseNotFound, erase_purchase, plan_purchase
from app.models import Purchase


class DeletePurchase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: Literal[True]
    expected_binding: str | None = None
    shared_history_confirmed: bool = False


def register(app, factory, runtime):
    @app.get("/api/purchases/{identifier}/deletion-preview")
    def preview(identifier: str):
        runtime.records()
        with factory() as session:
            try:
                plan = plan_purchase(session, identifier)
            except PurchaseNotFound:
                raise HTTPException(404, "Purchase not found") from None
            if plan.demo:
                raise HTTPException(409, "Sample purchases are managed by the demo reset")
            return plan.public()

    @app.post("/api/purchases/{identifier}/delete")
    def remove(identifier: str, body: DeletePurchase):
        with factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            records = runtime.records()
            purchase = session.get(Purchase, identifier)
            if purchase is None:
                if identifier in records:
                    return {"deleted": True, "purchase_id": identifier}
                raise HTTPException(404, "Purchase not found")
            plan = plan_purchase(session, identifier)
            if plan.demo:
                raise HTTPException(409, "Sample purchases are managed by the demo reset")
            if plan.active:
                raise HTTPException(409, plan.public()["blocked_reason"])
            if body.expected_binding is not None and body.expected_binding != plan.binding:
                raise HTTPException(409, "Deletion scope changed; reload the preview and confirm again")
            if plan.shared_run_ids and (body.expected_binding != plan.binding or not body.shared_history_confirmed):
                raise HTTPException(409, "Review and separately confirm removal of shared investigation history")
            runtime.record(purchase)
            try:
                counts = erase_purchase(session, plan)
            except DeletionConflict as exc:
                raise HTTPException(409, str(exc)) from None
            return {"deleted": True, "purchase_id": identifier, "removed": counts}
