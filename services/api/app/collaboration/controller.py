"""Bounded offline vertical slice. Live sponsor activation remains blocked, never simulated."""

import asyncio
from time import monotonic
from uuid import uuid4

from sqlalchemy import select

from app.claims.compose import compose
from app.collaboration import ledger, roles
from app.collaboration.contracts import CaseResult, CaseTask, EvidenceSnapshot, Finding, Status
from app.models import CaseRecord, CaseSnapshot, CollaborationRun, Product
from app.schemas import ProductInput

ACTIVE = ["queued", "investigating", "challenging", "building"]


def product_for_case(s, case):
    entity = s.get(Product, case.product_id)
    if entity is None:
        raise ValueError("Original product is unavailable; new review required")
    return ProductInput(**(entity.payload["product"] | case.payload.get("answers", {})))


def snapshot(s, case, recall):
    record = recall.model_dump(mode="json")
    material = recall.model_dump(mode="json", exclude={"fetched_at"})
    evidence = EvidenceSnapshot(
        source_id=recall.reference,
        publisher=recall.publisher,
        url=recall.official_url,
        fetched_at=recall.fetched_at,
        content_sha256=ledger.fingerprint(material),
        source_type="government",
        rule_version=roles.RULE_VERSION,
        excerpt=recall.excerpt,
        mode=recall.mode,
    )
    digest = ledger.fingerprint(evidence.model_dump(mode="json"))
    old = s.scalar(
        select(CaseSnapshot).where(CaseSnapshot.case_id == case.id, CaseSnapshot.fingerprint == digest)
    )
    if old is None:
        s.add(
            CaseSnapshot(
                case_id=case.id,
                fingerprint=digest,
                demo=case.demo,
                payload={"evidence": evidence.model_dump(mode="json"), "record": record},
            )
        )
    return evidence


def begin(s, case, key, mode):
    product = product_for_case(s, case)
    unavailable = False
    try:
        recall = roles.load_recall() if mode == "replay" else None
        evidence = snapshot(s, case, recall) if recall else None
    except (OSError, ValueError):
        evidence = None
        unavailable = True
    ledger.revise(
        s,
        case,
        {
            "product_hash": ledger.fingerprint(product.model_dump(mode="json")),
            "evidence_hashes": [evidence.content_sha256] if evidence else [],
            "rule_version": roles.RULE_VERSION,
            "skill_hash": ledger.fingerprint(roles.OFFLINE_SKILL),
        },
    )
    run = ledger.create_run(s, case, key, mode)
    run.payload = run.payload | {
        "product_ids": [case.product_id],
        "evidence": [evidence.model_dump(mode="json")] if evidence else [],
        "skill": roles.OFFLINE_SKILL if mode == "replay" else None,
    }
    if unavailable:
        run.status = "partial"
        run.payload = run.payload | {"warnings": ["Recorded source unavailable or invalid; review required."]}
        ledger.event(
            s,
            run,
            {
                "kind": "unavailable",
                "sender": "controller",
                "recipient": "controller",
                "status": "partial",
                "source_refs": [],
            },
        )
    return run


def run_view(s, run):
    case = s.get(CaseRecord, run.case_id)
    return {
        "id": run.id,
        "case_id": case.id,
        "product_ids": run.payload.get("product_ids", []),
        "revision": run.revision,
        "current_revision": case.current_revision,
        "status": run.status,
        "mode": run.payload["mode"],
        "warnings": run.payload.get("warnings", []),
        "board": run.payload.get("board", {}),
        "evidence": run.payload.get("evidence", []),
        "live_sponsor_proof": [],
        "skill": run.payload.get("skill"),
        "model_calls": run.payload.get("model_calls", 0),
        "task_requests": run.payload.get("task_requests", 0),
        "current": case.payload.get("current_run_id") == run.id,
    }


async def execute(factory, run_id, settings):
    with factory() as s:
        run = s.get(CollaborationRun, run_id)
        if run is None or run.status != "queued":
            return
        case = s.get(CaseRecord, run.case_id)
        started = monotonic()
        if run.payload["mode"] == "live":
            run.status = "partial"
            run.payload = run.payload | {
                "warnings": [
                    "Live team unavailable: BAND handshake, Agent37 worker, restricted AdaL runtime, "
                    "reviewed Finch delivery and Lyzr workspace configuration are not verified. "
                    "Use the separate V1 check or explicitly start offline replay."
                    if settings.collaboration_live_enabled
                    else "Paid team kill switch is off. No sponsor called; V1 and offline replay remain available."
                ]
            }
            ledger.event(
                s,
                run,
                {
                    "kind": "unavailable",
                    "sender": "controller",
                    "recipient": "controller",
                    "status": "partial",
                    "source_refs": [],
                },
            )
            s.commit()
            return
        try:
            async with asyncio.timeout(settings.collaboration_timeout_seconds):
                product = product_for_case(s, case)
                available = {e["source_id"] for e in run.payload["evidence"]}
                parent = None
                challenge = None
                recall = None
                review = None
                for index, (sender, recipient, kind, state) in enumerate(
                    [
                        ("controller", "scout", "source_investigation", "investigating"),
                        ("scout", "skeptic", "counterexample_review", "challenging"),
                        ("skeptic", "builder", "case_board_construction", "building"),
                    ]
                ):
                    remaining = min(
                        90000, int((settings.collaboration_timeout_seconds - (monotonic() - started)) * 1000)
                    )
                    if remaining <= 0:
                        raise TimeoutError
                    task = CaseTask.model_validate(
                        {
                            "case_id": case.id,
                            "task_id": str(uuid4()),
                            "revision": run.revision,
                            "sender": sender,
                            "recipient": recipient,
                            "kind": kind,
                            "parent_task_id": parent,
                            "deduplication_key": f"{run.id}:{recipient}",
                            "source_refs": sorted(available),
                            "allowed_capabilities": [
                                {
                                    "scout": "supported_source_read",
                                    "skeptic": "review_supplied_evidence",
                                    "builder": "build_sections",
                                }[recipient]
                            ],
                            "remaining_ms": remaining,
                            "mode": "replay",
                        }
                    )
                    run.status = state
                    run.payload = run.payload | {"task_requests": index + 1}
                    ledger.record_intent(s, run, task)
                    s.commit()  # Intent is durable before any role executes.
                    findings = []
                    status: Status = "completed"
                    missing = []
                    if recipient == "scout":
                        recall = await roles.scout(product)
                        if recall is None:
                            run.status = "partial"
                            run.payload = run.payload | {"warnings": ["No supported recall candidate found."]}
                            s.commit()
                            return
                        observed = snapshot(s, case, recall)
                        if observed.content_sha256 != run.payload["evidence"][0]["content_sha256"]:
                            raise ValueError("Evidence changed during run; fresh revision required")
                        findings = [Finding(code="candidate", source_ref=recall.reference)]
                    elif recipient == "skeptic":
                        assert recall is not None
                        challenge = roles.skeptic(product, recall)
                        findings = [
                            Finding.model_validate(
                                {
                                    "code": {
                                        "true": "condition_passed",
                                        "false": "condition_failed",
                                        "unknown": "condition_unknown",
                                    }[c.status],
                                    "condition": c.name,
                                    "source_ref": recall.reference,
                                }
                            )
                            for c in challenge.conditions
                        ]
                        missing = [c.name for c in challenge.conditions if c.status == "unknown"]
                        status = (
                            "rejected"
                            if challenge.status == "rejected"
                            else ("needs_information" if missing else "completed")
                        )
                    else:
                        assert recall is not None and challenge is not None
                        # Builder only consumes validated challenge findings. Text cannot grant authority.
                        assert review is not None
                        board = roles.builder(product, recall, review)
                        findings = [Finding(code="candidate", source_ref=recall.reference)]
                    result = CaseResult(
                        task_id=task.task_id,
                        case_id=case.id,
                        revision=run.revision,
                        provider="offline_rules",
                        mode="replay",
                        status=status,
                        findings=findings,
                        missing_conditions=missing,
                        source_refs=sorted(available),
                        duration_ms=min(90000, int((monotonic() - started) * 1000)),
                    )
                    if recipient == "skeptic":
                        assert challenge is not None and recall is not None
                        roles.validate_review(result, challenge, recall.reference)
                        review = result
                    ledger.record_result(s, run, task, result, available)
                    s.commit()  # Result precedes consumer/board update.
                    parent = task.task_id
                assert challenge is not None and recall is not None
                run.payload = run.payload | {"board": board}
                run.status = {"verified_match": "ready_for_review", "rejected": "rejected"}.get(
                    challenge.status, "needs_information" if board["question_field"] else "partial"
                )
                if run.status == "ready_for_review":
                    # Compose from confirmed identifiers/public instructions, never provider narrative.
                    safe_product = ProductInput(**roles.public_facts(product))
                    markdown = compose(safe_product, recall)["markdown"]
                    markdown += (
                        "\n\n## Team review\nOFFLINE REPLAY — local deterministic roles; "
                        "no live sponsor execution.\n" + board["challenge"]
                    )
                    ledger.prepare_draft(s, case, markdown)
                s.commit()
        except Exception as exc:  # noqa: BLE001 - task boundary must persist sanitized failures
            s.rollback()
            run = s.get(CollaborationRun, run_id)
            run.status = "partial"
            # Provider errors are not echoed; they can contain credentials/private payloads.
            run.payload = run.payload | {
                "warnings": [
                    "Team deadline exceeded; evidence preserved."
                    if isinstance(exc, TimeoutError)
                    else "Team result unavailable or invalid; evidence preserved."
                ]
            }
            ledger.event(
                s,
                run,
                {
                    "kind": "failure",
                    "sender": "controller",
                    "recipient": "controller",
                    "status": "timed_out" if isinstance(exc, TimeoutError) else "partial",
                    "source_refs": [],
                },
            )
            s.commit()
