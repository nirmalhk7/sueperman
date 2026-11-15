"""Opt-in team API. One product per case, explicit answers, server-owned revisions."""

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select

from app.collaboration import controller, ledger, roles
from app.db import view
from app.models import CaseDraft, CaseRecord, CollaborationEvent, CollaborationRun, Product
from app.schemas import Approval, CollaborationAnswer, CollaborationRequest, ProductInput


def register(app, factory, settings, get):
    def lock(s):
        # Serialize short admission/answer/approval transactions across processes.
        s.connection().exec_driver_sql("BEGIN IMMEDIATE")

    def active(s):
        if s.scalar(select(CollaborationRun).where(CollaborationRun.status.in_(controller.ACTIVE))):
            raise HTTPException(409, "A team run is active; wait before retrying")

    def old_request(s, key, signature):
        old = s.scalar(select(CollaborationRun).where(CollaborationRun.idempotency_key == key))
        if old:
            if old.payload.get("request_signature") != signature:
                raise HTTPException(409, "Idempotency key already used for different input")
            return controller.run_view(s, old)
        return None

    @app.post("/api/collaborations")
    def start(body: CollaborationRequest, background: BackgroundTasks):
        with factory() as s:
            lock(s)
            signature = ledger.fingerprint(body.model_dump())
            old = old_request(s, body.idempotency_key, signature)
            if old:
                return old
            active(s)
            product = get(s, Product, body.product_ids[0])
            facts = ProductInput(**product.payload["product"])
            if settings.collaboration_public_demo and not product.demo:
                raise HTTPException(422, "Public team demo accepts synthetic demo purchases only")
            if (
                product.payload.get("source_type") in {"image", "pdf"}
                and not facts.user_confirmed_identifiers
            ):
                raise HTTPException(422, "Confirm scanned identifiers before team investigation")
            if body.mode == "replay" and not settings.demo_mode:
                raise HTTPException(422, "Offline replay disabled")
            case = get(s, CaseRecord, body.case_id) if body.case_id else ledger.create_case(s, product.id)
            if case.product_id != product.id:
                raise HTTPException(409, "Case belongs to another product")
            run = controller.begin(s, case, body.idempotency_key, body.mode)
            run.payload = run.payload | {"request_signature": signature}
            s.commit()
            background.add_task(controller.execute, factory, run.id, settings)
            return controller.run_view(s, run)

    @app.get("/api/collaborations/{identifier}")
    def detail(identifier: str):
        with factory() as s:
            return controller.run_view(s, get(s, CollaborationRun, identifier))

    @app.get("/api/collaborations/{identifier}/events")
    def events(identifier: str):
        with factory() as s:
            get(s, CollaborationRun, identifier)
            return [
                {"id": e.id, "seq": e.seq, **e.payload}
                for e in s.scalars(
                    select(CollaborationEvent)
                    .where(CollaborationEvent.run_id == identifier)
                    .order_by(CollaborationEvent.seq)
                )
            ]

    @app.get("/api/collaborations/{identifier}/history")
    def history(identifier: str):
        with factory() as s:
            run = get(s, CollaborationRun, identifier)
            return {
                "revisions": [
                    view(r) | {"revision": r.revision, "fingerprint": r.fingerprint}
                    for r in s.scalars(
                        select(ledger.CaseRevisionRecord)
                        .where(ledger.CaseRevisionRecord.case_id == run.case_id)
                        .order_by(ledger.CaseRevisionRecord.revision)
                    )
                ],
                "snapshots": [
                    r.payload["evidence"]
                    for r in s.scalars(
                        select(ledger.CaseSnapshot).where(ledger.CaseSnapshot.case_id == run.case_id)
                    )
                ],
            }

    @app.post("/api/collaborations/{identifier}/answers")
    def answer(identifier: str, body: CollaborationAnswer, background: BackgroundTasks):
        with factory() as s:
            lock(s)
            signature = ledger.fingerprint({"run_id": identifier, **body.model_dump()})
            old = old_request(s, body.idempotency_key, signature)
            if old:
                return old
            active(s)
            run = get(s, CollaborationRun, identifier)
            case = get(s, CaseRecord, run.case_id)
            if (
                body.revision != case.current_revision
                or run.revision != case.current_revision
                or case.payload.get("current_run_id") != run.id
            ):
                raise HTTPException(409, "Stale case revision; refresh before answering")
            if run.status != "needs_information" or run.payload["board"].get("question_field") != body.field:
                raise HTTPException(409, "Answer only the requested supported field")
            try:
                value = body.value.strip()
                if not value:
                    raise ValueError("Empty answer")
                validated = ProductInput(
                    **(controller.product_for_case(s, case).model_dump() | {body.field: value})
                )
            except (ValidationError, ValueError):
                raise HTTPException(422, "Invalid answer format") from None
            case.payload = case.payload | {
                "answers": case.payload.get("answers", {})
                | {body.field: validated.model_dump(mode="json")[body.field]}
            }
            new = controller.begin(s, case, body.idempotency_key, run.payload["mode"])
            new.payload = new.payload | {"request_signature": signature, "parent_run_id": run.id}
            s.commit()
            background.add_task(controller.execute, factory, new.id, settings)
            return controller.run_view(s, new)

    def reviewed_case(s, identifier):
        run = get(s, CollaborationRun, identifier)
        case = get(s, CaseRecord, run.case_id)
        if (
            run.status != "ready_for_review"
            or run.revision != case.current_revision
            or case.payload.get("current_run_id") != run.id
        ):
            raise HTTPException(409, "Current case requires new review")
        product = controller.product_for_case(s, case)
        binding = ledger.current_revision(s, case)
        try:
            recall = roles.load_recall()
        except (OSError, ValueError):
            run.status = "partial"
            run.payload = run.payload | {"warnings": ["Recorded source unavailable; current review revoked."]}
            ledger.revise(s, case, binding.payload | {"evidence_hashes": []})
            s.commit()
            raise HTTPException(409, "Source unavailable; new review required") from None
        expected = {
            "product_hash": ledger.fingerprint(product.model_dump(mode="json")),
            "evidence_hashes": [ledger.fingerprint(recall.model_dump(mode="json", exclude={"fetched_at"}))],
            "rule_version": roles.RULE_VERSION,
            "skill_hash": ledger.fingerprint(roles.OFFLINE_SKILL),
        }
        if binding.fingerprint != ledger.fingerprint(expected):
            controller.snapshot(s, case, recall)
            ledger.revise(s, case, expected)
            s.commit()
            raise HTTPException(409, "Product, evidence, rule or skill changed; new review required")
        draft = s.scalar(
            select(CaseDraft).where(CaseDraft.case_id == case.id, CaseDraft.revision == case.current_revision)
        )
        if draft is None:
            raise HTTPException(409, "Draft not prepared")
        return case, draft

    @app.post("/api/collaborations/{identifier}/claim-packet")
    def packet(identifier: str):
        with factory() as s:
            lock(s)
            _, draft = reviewed_case(s, identifier)
            return view(draft) | {"revision": draft.revision}

    @app.post("/api/collaborations/{identifier}/approve-local")
    def approve(identifier: str, body: Approval):
        with factory() as s:
            lock(s)
            case, draft = reviewed_case(s, identifier)
            ledger.approve_draft(s, case, draft)
            s.commit()
            return view(draft)

    @app.post("/api/collaborations/{identifier}/export")
    def export(identifier: str):
        with factory() as s:
            lock(s)
            case, draft = reviewed_case(s, identifier)
            try:
                markdown = ledger.export_draft(s, case, draft)
            except ValueError:
                raise HTTPException(409, "Approve current draft locally before export") from None
            s.commit()
            return Response(
                markdown,
                media_type="text/markdown",
                headers={"Content-Disposition": 'attachment; filename="sueperman-team-draft.md"'},
            )
