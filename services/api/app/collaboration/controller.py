"""Bounded replay and configured live team; deterministic conditions retain authority."""

import asyncio
from time import monotonic
from uuid import uuid4

from app.claims.compose import compose
from app.collaboration import live
from app.collaboration.contracts import CaseResult, CaseTask, EvidenceSnapshot, Finding, Status
from app.collaboration.ledger import (
    LOCAL_POLICY,
    LOCAL_SKILL_HASH,
    RULE_VERSION,
    current,
    digest,
    persist_intent,
    persist_result,
    revision_for,
)
from app.collaboration.revisions import fixture_binding, primary_record, source_binding
from app.collaboration.runtime_adapters import validate_role
from app.matching.recall import match_recall
from app.models import Collaboration, CollaborationEvidence, CollaborationRevision, Product, now
from app.providers.cpsc import FixtureRecallSource
from app.schemas import MatchResult, ProductInput, RecallRecord

# Only these product facts cross the role boundary. No merchant, receipt, order or unrelated purchase.
FACT_FIELDS = {
    "product_name",
    "brand",
    "model_number",
    "serial_prefix",
    "batch",
    "date_purchased",
    "region",
    "upc",
}
PRIORITY = LOCAL_POLICY["question_priority"]
PROVIDERS = ["band", "agent37", "adal", "finch", "lyzr"]


def sanitized(product):
    return {k: v for k, v in product.items() if k in FACT_FIELDS}


def next_question(result):
    unknown = {c.name for c in result.conditions if c.status == "unknown"}
    field = next((name for name in PRIORITY if name in unknown), None)
    if not field or result.status == "rejected":
        return None
    return {"field": field, "text": f"What is the {field.replace('_', ' ')} shown on your product or record?"}


def verify_result(result, match):
    """Never render arbitrary model prose; every finding must be justified by fixed conditions."""
    conditions = {c.name: c.status for c in match.conditions}
    for finding in result.findings:
        if (
            finding.code in {"excluded_condition", "unknown_condition", "checklist_exhausted"}
            and finding.source_ref not in result.source_refs
        ):
            raise ValueError("Challenge requires a supplied citation")
        if finding.code == "excluded_condition" and conditions.get(finding.condition) != "false":
            raise ValueError("Unsupported exclusion")
        if finding.code == "unknown_condition" and conditions.get(finding.condition) != "unknown":
            raise ValueError("Unsupported missing condition")
        if finding.code == "checklist_exhausted" and any(v != "true" for v in conditions.values()):
            raise ValueError("Incomplete checklist")
    if result.role in {"skeptic", "builder"} and result.status not in {"partial", "failed", "timed_out"}:
        required = {
            (name, "excluded_condition" if value == "false" else "unknown_condition")
            for name, value in conditions.items()
            if value != "true"
        }
        observed = {(f.condition, f.code) for f in result.findings}
        if not required.issubset(observed):
            raise ValueError("Reviewer omitted a required condition")
        if conditions and not required and not any(f.code == "checklist_exhausted" for f in result.findings):
            raise ValueError("Reviewer omitted the completed checklist")
    expected = next_question(match)
    if result.missing_conditions and result.missing_conditions != ([expected["field"]] if expected else []):
        raise ValueError("Question violates deterministic priority")
    if result.status == "completed" and result.role == "builder" and match.status != "verified_match":
        raise ValueError("Builder cannot approve false or unknown conditions")


async def replay_role(task, match, prior):
    """Three distinct replay roles exchange typed results; this is not sponsor execution."""
    refs = task.source_refs
    source = refs[0] if refs else None
    findings = []
    missing = []
    status: Status = "completed"
    if task.recipient == "scout":
        findings = [Finding(code="candidate" if refs else "no_candidate", source_ref=source)]
    elif task.recipient == "skeptic":
        if not prior or prior.role != "scout":
            raise ValueError("Skeptic requires Scout reply")
        findings = [
            Finding(
                code="excluded_condition" if c.status == "false" else "unknown_condition",
                condition=c.name,
                source_ref=source,
            )
            for c in match.conditions
            if c.status != "true"
        ]
        if not findings:
            findings = [Finding(code="checklist_exhausted" if refs else "no_candidate", source_ref=source)]
    else:
        if not prior or prior.role != "skeptic":
            raise ValueError("Builder requires Skeptic reply")
        findings = prior.findings
        question = next_question(match)
        missing = [question["field"]] if question else []
        status = (
            "completed"
            if match.status == "verified_match"
            else "rejected"
            if match.status == "rejected"
            else "needs_information"
        )
    return CaseResult(
        task_id=task.task_id,
        case_id=task.case_id,
        revision=task.revision,
        provider="local_replay",
        role=task.recipient,
        mode="replay",
        status=status,
        findings=findings,
        missing_conditions=missing,
        source_refs=refs,
    )


async def execute(factory, case_id, settings):
    started = monotonic()
    team = None
    with factory() as s:
        case = s.get(Collaboration, case_id)
        if not case or case.status != "queued":
            return
        case.status = "investigating"
        s.commit()
        try:
            async with asyncio.timeout(settings.collaboration_run_seconds):
                is_live = case.payload["mode"] == "live"
                entity = s.get(Product, case.product_id)
                facts = case.payload["facts"]
                product = ProductInput(**facts)
                skill_hash = LOCAL_SKILL_HASH
                scout_result = None
                scout_entry = None
                if is_live:
                    unavailable = live.blockers(settings)
                    if unavailable:
                        case.status = "partial"
                        case.payload = case.payload | {
                            "blocked_providers": list(unavailable),
                            "warnings": [f"{provider}: {reason}" for provider, reason in unavailable.items()],
                        }
                        s.commit()
                        return
                    team = live.LiveTeam(settings)
                    skill_hash = team.skill_hash
                    # A non-exportable discovery revision owns the source request.
                    # The verified evidence creates the final material case revision.
                    case.current_revision = revision_for(facts, [], skill_hash=skill_hash)
                    discovery = CaseTask(
                        case_id=case.id,
                        task_id=str(uuid4()),
                        revision=case.current_revision,
                        sender="controller",
                        recipient="scout",
                        task_kind="source_investigation",
                        deduplication_key=f"{case.id}:{case.current_revision}:scout",
                        parent_task_id=None,
                        allowed_capabilities=["read_supplied_evidence"],
                        source_refs=["26-792"],
                        mode="live",
                        remaining_seconds=max(
                            0.001, settings.collaboration_run_seconds - (monotonic() - started)
                        ),
                    )
                    scout_entry = persist_intent(s, case, discovery)
                    case.payload = case.payload | {"model_calls": 0, "task_requests": 1}
                    s.commit()
                    await team.__aenter__()
                    discovery = discovery.model_copy(
                        update={
                            "remaining_seconds": max(
                                0.001, settings.collaboration_run_seconds - (monotonic() - started)
                            )
                        }
                    )
                    output, receipt = await team.request(discovery, {"facts": facts})
                    records = live.source_records(output)
                    scout_result = validate_role(output["result"], discovery, "agent37")
                    s.add(
                        CollaborationEvidence(
                            case_id=case.id,
                            revision=case.current_revision,
                            source_ref="26-792",
                            demo=case.demo,
                            payload=records[0].model_dump(mode="json"),
                        )
                    )
                    s.commit()
                    persist_result(s, case, scout_entry, scout_result)
                    scout_entry.payload = scout_entry.payload | {
                        "routing": receipt,
                        "execution": output.get("execution"),
                    }
                    s.commit()
                else:
                    primary = primary_record(s, case.product_id)
                    records = (
                        [
                            RecallRecord.model_validate(primary.payload["recall"]).model_copy(
                                update={"mode": "replay"}
                            )
                        ]
                        if primary
                        else await FixtureRecallSource().search(product)
                    )
                recall = records[0] if records else None
                match = match_recall(product, recall) if recall else MatchResult(status="needs_review")
                evidence = []
                if recall:
                    evidence = [
                        EvidenceSnapshot(
                            id=recall.reference,
                            publisher=recall.publisher,
                            url=recall.official_url,
                            fetched_at=recall.fetched_at,
                            content_sha256=digest(recall.model_dump(mode="json")),
                            rule_version=RULE_VERSION,
                            excerpt=recall.excerpt,
                            mode="live" if is_live else "replay",
                        ).model_dump(mode="json")
                    ]
                revision = revision_for(facts, evidence, skill_hash=skill_hash)
                case.current_revision = revision
                row = current(s, case)
                if row is None:
                    row = CollaborationRevision(
                        case_id=case.id,
                        revision=revision,
                        demo=case.demo,
                        payload={
                            "facts": facts,
                            "original_product_hash": digest(entity.payload["product"]),
                            "source_binding": source_binding(s, case.product_id),
                            "fixture_binding": fixture_binding(),
                            "evidence": evidence,
                            "rule_version": RULE_VERSION,
                            "skill_hash": skill_hash,
                            "skill_package_path": settings.finch_package_path if is_live else None,
                            "skill_identity": team.manifest.identity
                            if team
                            else "local-counterexample-policy",
                            "skill_version": team.manifest.version if team else "1",
                            "skill_license": team.manifest.license if team else None,
                            "origin_scout_task": scout_entry.id if scout_entry else None,
                            "conditions": [c.model_dump(mode="json") for c in match.conditions],
                            "packet": None,
                            "approval": None,
                            "board": {},
                            "question": None,
                        },
                    )
                    s.add(row)
                    for item in evidence:
                        s.add(
                            CollaborationEvidence(
                                case_id=case.id,
                                revision=revision,
                                source_ref=item["id"],
                                demo=case.demo,
                                payload=item,
                            )
                        )
                    s.commit()
                prior = scout_result
                parent = scout_entry.id if scout_entry else None
                for role, sender, kind, capability, state in [
                    (
                        "scout",
                        "controller",
                        "source_investigation",
                        "read_supplied_evidence",
                        "investigating",
                    ),
                    ("skeptic", "scout", "counterexample_review", "challenge_conditions", "challenging"),
                    ("builder", "skeptic", "case_board_construction", "build_sections", "building"),
                ]:
                    if is_live and role == "scout":
                        continue
                    case.status = state
                    task = CaseTask.model_validate(
                        {
                            "case_id": case.id,
                            "task_id": str(uuid4()),
                            "revision": revision,
                            "sender": sender,
                            "recipient": role,
                            "task_kind": kind,
                            "parent_task_id": parent,
                            "deduplication_key": f"{case.id}:{revision}:{role}",
                            "allowed_capabilities": [capability],
                            "source_refs": [e["id"] for e in evidence],
                            "mode": "live" if is_live else "replay",
                            "remaining_seconds": max(
                                0.001, settings.collaboration_run_seconds - (monotonic() - started)
                            ),
                        }
                    )
                    entry = persist_intent(s, case, task)
                    if team:
                        case.payload = case.payload | {
                            "model_calls": case.payload.get("model_calls", 0) + 1,
                            "task_requests": case.payload.get("task_requests", 0) + 1,
                        }
                        s.commit()
                        assert prior is not None
                        context = {
                            "facts": facts,
                            "evidence": evidence,
                            "match": match.model_dump(mode="json"),
                            "prior": prior.model_dump(mode="json", exclude={"provider_reference"}),
                        }
                        output, receipt = await team.request(task, context)
                        result = validate_role(
                            output["result"], task, "adal" if role == "skeptic" else "lyzr"
                        )
                        if role == "skeptic" and output.get("skill_hash") != skill_hash:
                            raise ValueError("Skeptic did not invoke the pinned skill")
                        entry.payload = entry.payload | {"routing": receipt}
                    else:
                        result = await replay_role(task, match, prior)
                    verify_result(result, match)
                    persist_result(s, case, entry, result)
                    if result.status in {"partial", "failed", "timed_out"}:
                        raise ValueError("Incomplete role result")
                    prior, parent = result, entry.id
                assert prior is not None
                exclusions = [f.condition for f in prior.findings if f.code == "excluded_condition"]
                unknown = [f.condition for f in prior.findings if f.code == "unknown_condition"]
                question = next_question(match)
                state = (
                    "ready_for_review"
                    if match.status == "verified_match"
                    else "rejected"
                    if match.status == "rejected"
                    else "needs_information"
                )
                packet = (
                    compose(product, recall) | {"generated_at": now()}
                    if state == "ready_for_review" and recall
                    else None
                )
                board = {
                    "finding": f"Scout proposed CPSC recall {recall.reference} for review."
                    if recall
                    else "No supported recall candidate found.",
                    "challenge": "Excluded by official conditions: " + ", ".join(exclusions)
                    if exclusions
                    else "Unresolved conditions: " + ", ".join(unknown)
                    if unknown
                    else "No additional supported exclusion found in the fixed checklist."
                    if recall
                    else "No candidate to challenge.",
                    "missing_information": question["text"]
                    if question
                    else "No identification question. Review remedy documents separately."
                    if recall
                    else "Supported source evidence is needed.",
                    "decision": {
                        "ready_for_review": "Deterministic checks passed. Review the local draft and required remedy evidence.",
                        "rejected": "Official evidence excludes this product. No draft can be approved.",
                        "needs_information": "Eligibility remains unresolved. No draft can be approved.",
                    }[state],
                    "evidence": evidence,
                }
                row.payload = row.payload | {
                    "board": board,
                    "question": question,
                    "packet": packet,
                    "approval": None,
                }
                case.status = state
                case.payload = case.payload | {
                    "elapsed_ms": round((monotonic() - started) * 1000),
                    "model_calls": case.payload.get("model_calls", 0) if is_live else 0,
                    "task_requests": 3,
                    "blocked_providers": [],
                }
                s.commit()
        except Exception:  # noqa: BLE001 — worker boundary: preserve evidence, never expose provider errors or secrets.
            s.rollback()
            case = s.get(Collaboration, case_id)
            case.status = "partial"
            case.payload = case.payload | {
                "warnings": [
                    "Team timed out or returned an unavailable/invalid result; preserved evidence requires review."
                ]
            }
            s.commit()

        finally:
            if team is not None:
                try:
                    async with asyncio.timeout(5):
                        await team.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001 — cleanup uncertainty prevents complete-team labeling.
                    case.status = "partial"
                    case.payload = case.payload | {
                        "warnings": ["Live runtime shutdown unconfirmed; no automatic retry."]
                    }
                elapsed = round((monotonic() - started) * 1000)
                if elapsed > settings.collaboration_run_seconds * 1000:
                    case.status = "partial"
                    case.payload = case.payload | {
                        "warnings": ["Team run deadline exceeded; review partial evidence."]
                    }
                case.payload = case.payload | {"elapsed_ms": elapsed}
                s.commit()
