"""Catch destructive migration, duplicate/stale delivery and lost approval history."""

import json
import sqlite3

import pytest
from sqlalchemy import inspect, select


def ledger():
    try:
        from app.collaboration import ledger

        return ledger
    except ImportError:
        pytest.fail("V2 persistent ledger missing")


def test_additive_migration_preserves_populated_v1_database(tmp_path):
    path = tmp_path / "v1.db"
    # Real populated V1 schema, created before importing any collaboration model.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models import (
        AgentRun,
        AuditEvent,
        ClaimPacket,
        EligibilityAssessment,
        Opportunity,
        Product,
        Purchase,
        ReceiptOCRUsage,
        SourceEvidence,
    )

    engine = create_engine(f"sqlite:///{path}")
    for model in [
        ReceiptOCRUsage,
        Purchase,
        Product,
        Opportunity,
        SourceEvidence,
        EligibilityAssessment,
        ClaimPacket,
        AgentRun,
        AuditEvent,
    ]:
        model.__table__.create(engine)
    assert "case_records" not in inspect(engine).get_table_names()
    factory = sessionmaker(engine)
    with factory() as s:
        purchase = Purchase(import_key="existing", payload={"merchant": "Private"})
        s.add(purchase)
        s.flush()
        product = Product(purchase_id=purchase.id, payload={"product": {"product_name": "Existing"}})
        s.add(product)
        s.flush()
        opp = Opportunity(product_id=product.id, kind="recall", source_id="old", official_url="old")
        s.add(opp)
        s.flush()
        packet = ClaimPacket(opportunity_id=opp.id, payload={"markdown": "User historical draft"})
        s.add(packet)
        s.commit()
    engine.dispose()

    def rows():
        with sqlite3.connect(path) as c:
            return {
                name: c.execute(f'SELECT * FROM "{name}" ORDER BY id').fetchall()
                for name in ("purchases", "products", "opportunities", "claim_packets")
            }

    before = rows()
    l = ledger()
    engine = create_engine(f"sqlite:///{path}")
    l.migrate(engine)
    l.migrate(engine)
    assert rows() == before
    assert {
        "case_records",
        "case_revisions",
        "collaboration_runs",
        "collaboration_tasks",
        "collaboration_events",
        "case_snapshots",
        "case_drafts",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()


def test_ledger_deduplicates_results_rejects_stale_and_preserves_history(tmp_path):
    l = ledger()
    from app.collaboration.contracts import CaseResult, CaseTask
    from app.db import database
    from app.models import Product, Purchase

    engine, factory = database(f"sqlite:///{tmp_path}/ledger.db")
    with factory() as s:
        p = Purchase(import_key="p")
        s.add(p)
        s.flush()
        product = Product(purchase_id=p.id, payload={"product": {"product_name": "Power bank"}})
        s.add(product)
        s.flush()
        case = l.create_case(s, product.id)
        revision = l.revise(
            s,
            case,
            {
                "product_hash": "a" * 64,
                "evidence_hashes": [],
                "rule_version": "26-792-v1",
                "skill_hash": "b" * 64,
            },
        )
        run = l.create_run(s, case, "key", "replay")
        task = CaseTask(
            case_id=case.id,
            task_id="task",
            revision=1,
            sender="controller",
            recipient="scout",
            kind="source_investigation",
            deduplication_key="one",
            remaining_ms=1000,
            mode="replay",
        )
        l.record_intent(s, run, task)
        result = CaseResult(
            task_id="task",
            case_id=case.id,
            revision=1,
            provider="offline_rules",
            mode="replay",
            status="completed",
        )
        assert l.record_result(s, run, task, result, set()) is True
        assert l.record_result(s, run, task, result, set()) is False
        events = s.scalars(select(l.CollaborationEvent).where(l.CollaborationEvent.run_id == run.id)).all()
        assert [e.seq for e in events] == [1, 2]
        assert len(s.scalars(select(l.CollaborationTask)).all()) == 1
        draft = l.prepare_draft(s, case, "Local draft; not a submission.")
        l.approve_draft(s, case, draft)
        assert l.export_draft(s, case, draft) == "Local draft; not a submission."
        l.revise(s, case, revision.payload | {"skill_hash": "c" * 64})
        with pytest.raises(ValueError, match="revision"):
            l.record_result(s, run, task, result, set())
        with pytest.raises(ValueError, match="review"):
            l.export_draft(s, case, draft)
        assert s.get(l.CaseRevisionRecord, revision.id).payload["skill_hash"] == "b" * 64
        assert draft.payload["markdown"] == "Local draft; not a submission."
        assert len(s.scalars(select(l.CaseRevisionRecord)).all()) == 2
        s.commit()
    with factory() as s:
        assert len(s.scalars(select(l.CollaborationTask)).all()) == 1
        assert "Private" not in json.dumps([e.payload for e in s.scalars(select(l.CollaborationEvent))])
    engine.dispose()


def test_closed_run_rejects_late_result_and_seventh_task(tmp_path):
    l = ledger()
    from app.collaboration.contracts import CaseResult, CaseTask
    from app.db import database
    from app.models import Product, Purchase

    engine, factory = database(f"sqlite:///{tmp_path}/bounds.db")
    with factory() as s:
        purchase = Purchase(import_key="limits")
        s.add(purchase)
        s.flush()
        product = Product(purchase_id=purchase.id)
        s.add(product)
        s.flush()
        case = l.create_case(s, product.id)
        l.revise(
            s,
            case,
            {"product_hash": "a" * 64, "evidence_hashes": [], "rule_version": "v1", "skill_hash": "b" * 64},
        )
        run = l.create_run(s, case, "limits", "replay")
        tasks = []
        for index in range(6):
            task = CaseTask(
                case_id=case.id,
                task_id=f"task-{index}",
                revision=1,
                sender="controller",
                recipient="scout",
                kind="source_investigation",
                deduplication_key=str(index),
                remaining_ms=1000,
                mode="replay",
            )
            l.record_intent(s, run, task)
            tasks.append(task)
        seventh = tasks[0].model_copy(update={"task_id": "seventh", "deduplication_key": "seventh"})
        with pytest.raises(ValueError, match="budget"):
            l.record_intent(s, run, seventh)
        run.status = "partial"
        result = CaseResult(
            task_id="task-0",
            case_id=case.id,
            revision=1,
            provider="offline_rules",
            mode="replay",
            status="completed",
        )
        with pytest.raises(ValueError, match="closed"):
            l.record_result(s, run, tasks[0], result, set())
    engine.dispose()
