"""Live sponsor roles, immutable official evidence and application-owned decisions."""

import asyncio
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic
from uuid import uuid4

from dotenv import dotenv_values

from app.claims.compose import compose
from app.collaboration import controller, ledger, roles
from app.collaboration.contracts import CaseResult, CaseTask, Finding
from app.collaboration.live_providers import LyzrRoles, PublicScout
from app.collaboration.live_transport import LiveTransport
from app.config import ROOT
from app.matching.normalize import normalize_model
from app.matching.recall import match_recall
from app.models import CaseRecord, CollaborationRun
from app.providers.cpsc import CPSCRecallSource
from app.schemas import MatchResult, ProductInput, RecallRecord

POLICY = {"identity": "live-official-evidence", "version": 1,
          "roles": ["agent37", "lyzr-reviewer", "lyzr-builder"], "rules": roles.RULE_VERSION}


def credentials(settings):
    if not settings.collaboration_live_enabled:
        raise ValueError("Live investigation is disabled")
    values = dotenv_values(ROOT / ".env") | dict(os.environ)
    names = {"manager": "CONTROLLER", "researcher": "SCOUT", "skeptic": "SKEPTIC", "builder": "BUILDER"}
    actors = {
        role: {"agent_id": values.get(f"BAND_{prefix}_AGENT_ID"), "api_key": values.get(f"BAND_{prefix}_API_KEY")}
        for role, prefix in names.items()}
    result = {"room_id": values.get("BAND_ROOM_ID"), "actors": actors}
    if not result["room_id"] or not all(all(actor.values()) for actor in actors.values()):
        raise ValueError("Live messaging credentials are incomplete")
    if len({actor["agent_id"] for actor in actors.values()}) != 4:
        raise ValueError("Live messaging identities must be distinct")
    LyzrRoles(settings.lyzr_api_key, settings.lyzr_review_agent_id, settings.lyzr_agent_id,
              settings.lyzr_user_id, endpoint=settings.lyzr_api_url)
    PublicScout(settings.agent37_api_key, instance_id=settings.agent37_instance_id)
    return result


async def current_recall(product, source_id, settings):
    # Approval/export never calls paid roles, and never reads recorded fixtures.
    with TemporaryDirectory(prefix="sueperman-review-") as folder:
        records = await CPSCRecallSource(cache_dir=Path(folder), reviewed_notices=settings.p1_enabled).search(product)
    return next(record for record in records if record.reference == source_id)


def binding(product, evidence):
    return {"product_hash": ledger.fingerprint(product.model_dump(mode="json")),
        "evidence_hashes": [evidence.content_sha256], "rule_version": roles.RULE_VERSION,
        "skill_hash": ledger.fingerprint(POLICY)}


def reviewed_result(task, challenge, recall):
    return CaseResult(task_id=task.task_id, case_id=task.case_id, revision=task.revision,
        provider="lyzr", mode="live", status="rejected" if challenge.status == "rejected" else
        "needs_information" if challenge.status != "verified_match" else "completed",
        findings=[Finding.model_validate({"code": {"true": "condition_passed", "false": "condition_failed",
            "unknown": "condition_unknown"}[c.status], "condition": c.name, "source_ref": recall.reference})
            for c in challenge.conditions],
        missing_conditions=[c.name for c in challenge.conditions if c.status == "unknown"],
        source_refs=[recall.reference])


def board_for(product, recall, challenge, advice):
    missing = [c.name for c in challenge.conditions if c.status == "unknown"]
    false = [c.name for c in challenge.conditions if c.status == "false"]
    question = roles.next_question(missing) if challenge.status == "needs_review" else None
    return {"finding": f"Scout found official CPSC recall {recall.reference}.",
        "challenge": f"Model {product.model_number} differs from official affected model(s): {', '.join(recall.models)}."
        if "model_number" in false else "Supported exclusion: " + ", ".join(false) if false else
        "Unresolved source conditions: " + ", ".join(missing) if missing else
        "Exact identifiers satisfy the supported official conditions.",
        "review_note": advice.review_note, "missing_information": missing,
        "question_field": question,
        "question": f"What is the {question.replace('_', ' ')} printed on your product or record?" if question else None,
        "decision": challenge.status, "conditions": [c.model_dump(mode="json") for c in challenge.conditions]}


async def execute(factory, run_id, settings):
    with factory() as s:
        run = s.get(CollaborationRun, run_id)
        case = s.get(CaseRecord, run.case_id)
        started = monotonic()
        try:
            async with asyncio.timeout(settings.collaboration_timeout_seconds):
                config = credentials(settings)
                product = controller.product_for_case(s, case)
                scout = PublicScout(settings.agent37_api_key, instance_id=settings.agent37_instance_id,
                                    reviewed_notices=settings.p1_enabled)
                lyzr = LyzrRoles(settings.lyzr_api_key, settings.lyzr_review_agent_id, settings.lyzr_agent_id,
                                 settings.lyzr_user_id, endpoint=settings.lyzr_api_url)
                records, receipts = [], []
                recall: RecallRecord | None = None
                challenge: MatchResult | None = None
                advice = review = None

                async def investigate(task):
                    nonlocal records
                    records, receipt = await scout.investigate(ProductInput(**roles.public_facts(product)), run.id, case.id)
                    receipts.append(receipt)
                    return CaseResult(task_id=task.task_id, case_id=case.id, revision=task.revision,
                        provider="agent37", mode="live", status="completed", source_refs=[r.reference for r in records],
                        findings=[Finding(code="candidate", source_ref=r.reference) for r in records])

                async def scrutinize(task):
                    nonlocal advice, review
                    assert recall is not None and challenge is not None
                    advice = await lyzr.review(task, {"product": roles.public_facts(product),
                        "evidence": recall.model_dump(mode="json"),
                        "conditions": [c.model_dump(mode="json") for c in challenge.conditions]})
                    if advice.uncertainty:
                        raise ValueError("Reviewer requires manual source review")
                    review = reviewed_result(task, challenge, recall)
                    return review

                async def build(task):
                    assert recall is not None and review is not None
                    expected = {k: review.model_dump(mode="json")[k] for k in
                                ("status", "findings", "missing_conditions", "source_refs")}
                    return await lyzr.build(task, {"product": roles.public_facts(product),
                        "evidence": recall.model_dump(mode="json"), "validated_review": expected})

                async with LiveTransport(config, {"researcher": investigate, "skeptic": scrutinize, "builder": build}) as transport:
                    parent = None
                    for index, (sender, recipient, kind, state) in enumerate([
                        ("controller", "scout", "source_investigation", "investigating"),
                        ("scout", "skeptic", "counterexample_review", "challenging"),
                        ("skeptic", "builder", "case_board_construction", "building")]):
                        task = CaseTask.model_validate({"case_id": case.id, "task_id": str(uuid4()), "revision": run.revision,
                            "sender": sender, "recipient": recipient, "kind": kind, "parent_task_id": parent,
                            "deduplication_key": f"{run.id}:{recipient}", "source_refs": [recall.reference] if recall else [],
                            "allowed_capabilities": [{"scout": "supported_source_read", "skeptic": "review_supplied_evidence",
                                "builder": "build_sections"}[recipient]], "mode": "live",
                            "remaining_ms": max(1, min(90000, int((settings.collaboration_timeout_seconds - (monotonic() - started)) * 1000)))})
                        run.status = state
                        run.payload = run.payload | {"task_requests": index + 1}
                        ledger.record_intent(s, run, task)
                        s.commit()
                        result = await transport.exchange(task, ledger.current_revision(s, case).fingerprint)
                        if result.status in {"failed", "partial", "timed_out"}:
                            raise ValueError("Role unavailable")
                        available = {r.reference for r in records}
                        ledger.record_result(s, run, task, result, available)
                        s.commit()
                        parent = task.task_id
                        if recipient == "scout":
                            exact = [r for r in records if normalize_model(product.model_number) and
                                     normalize_model(product.model_number) in [normalize_model(m) for m in r.models]]
                            candidates = exact or records
                            if len(candidates) != 1:
                                raise ValueError("No unique supported official candidate")
                            recall = candidates[0]
                            evidence = controller.snapshot(s, case, recall)
                            ledger.revise(s, case, binding(product, evidence))
                            run.revision = case.current_revision
                            run.payload = run.payload | {"evidence": [evidence.model_dump(mode="json")], "skill": POLICY}
                            challenge = match_recall(product, recall)
                            s.commit()
                assert recall is not None and challenge is not None and advice is not None
                board = board_for(product, recall, challenge, advice)
                run.status = {"verified_match": "ready_for_review", "rejected": "rejected"}.get(
                    challenge.status, "needs_information" if board["question_field"] else "partial")
                run.payload = run.payload | {"board": board, "receipts": receipts + list(lyzr.receipts.values()) + transport.receipts,
                    "model_calls": len(lyzr.attempted), "live_sponsor_proof": ["band", "agent37", "lyzr-reviewer", "lyzr-builder"]}
                if run.status == "ready_for_review":
                    markdown = compose(ProductInput(**roles.public_facts(product)), recall)["markdown"]
                    ledger.prepare_draft(s, case, markdown + "\n\n## Team review\nCurrent official evidence reviewed. " + board["challenge"])
                s.commit()
        except Exception as exc:  # noqa: BLE001 - provider errors may include secrets
            s.rollback()
            run = s.get(CollaborationRun, run_id)
            run.status = "partial"
            run.payload = run.payload | {"warnings": ["Investigation deadline exceeded; evidence preserved." if isinstance(exc, TimeoutError)
                else "Live investigation unavailable or invalid; evidence preserved. Review sources before retrying."]}
            ledger.event(s, run, {"kind": "failure", "sender": "controller", "recipient": "controller",
                "status": "partial", "source_refs": []})
            s.commit()
