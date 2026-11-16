import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from app.collaboration.contracts import CaseResult, CaseTask
from app.collaboration.ledger import digest, persist_intent, persist_result
from app.db import database
from app.models import Base, ClaimPacket, Collaboration, CollaborationTask, Opportunity, Product, Purchase


def test_additive_migration_preserves_populated_v1_database(tmp_path):
    url = f"sqlite:///{tmp_path}/populated-v1.db"
    engine = create_engine(url)
    old_tables = [t for name, t in Base.metadata.tables.items() if not name.startswith("collaboration")]
    Base.metadata.create_all(engine, tables=old_tables)
    with Session(engine) as s:
        purchase = Purchase(import_key="private-original", payload={"keep": "purchase"})
        s.add(purchase)
        s.flush()
        product = Product(purchase_id=purchase.id, payload={"keep": "product"})
        s.add(product)
        s.flush()
        opp = Opportunity(
            product_id=product.id,
            kind="recall",
            source_id="26-792",
            official_url="original",
            payload={"keep": "opportunity"},
        )
        s.add(opp)
        s.flush()
        packet = ClaimPacket(
            opportunity_id=opp.id, payload={"status": "approved_local", "markdown": "historical packet"}
        )
        s.add(packet)
        s.commit()
        packet_id = packet.id
    before = {}
    with engine.connect() as conn:
        for table in old_tables:
            before[table.name] = list(conn.execute(text(f"SELECT * FROM {table.name}")))
    engine.dispose()
    migrated, factory = database(url)
    with migrated.connect() as conn:
        for table in old_tables:
            assert list(conn.execute(text(f"SELECT * FROM {table.name}"))) == before[table.name]
        assert "collaboration_tasks" in inspect(conn).get_table_names()
        assert conn.execute(text("PRAGMA foreign_key_check")).all() == []
    with factory() as s:
        assert s.get(ClaimPacket, packet_id).payload["markdown"] == "historical packet"
    migrated.dispose()


def test_duplicate_stale_wrong_case_and_fabricated_citations_cannot_update_ledger(tmp_path):
    engine, factory = database(f"sqlite:///{tmp_path}/ledger.db")
    with factory() as s:
        purchase = Purchase(import_key="synthetic")
        s.add(purchase)
        s.flush()
        product = Product(purchase_id=purchase.id)
        s.add(product)
        s.flush()
        case = Collaboration(
            product_id=product.id, idempotency_key="case", current_revision=digest("revision")
        )
        s.add(case)
        s.commit()
        task = CaseTask(
            case_id=case.id,
            task_id="task",
            revision=case.current_revision,
            sender="controller",
            recipient="scout",
            task_kind="source_investigation",
            deduplication_key="unique",
            allowed_capabilities=["read_supplied_evidence"],
            source_refs=["26-792"],
            remaining_seconds=80,
            mode="replay",
        )
        row = persist_intent(s, case, task)
        assert persist_intent(s, case, task).id == row.id
        base = {
            "task_id": "task",
            "case_id": case.id,
            "revision": case.current_revision,
            "provider": "local_replay",
            "role": "scout",
            "mode": "replay",
            "status": "completed",
            "findings": [],
            "source_refs": ["26-792"],
        }
        for change in [
            {"revision": digest("stale")},
            {"case_id": "other"},
            {"source_refs": ["invented"]},
            {"role": "builder"},
            {"provider": "adal"},
            {"mode": "live"},
        ]:
            with pytest.raises(ValueError):
                persist_result(s, case, row, CaseResult(**(base | change)))
            assert "result" not in row.payload
        result = CaseResult(**base)
        persist_result(s, case, row, result)
        persist_result(s, case, row, result)
        assert len(s.scalars(select(CollaborationTask)).all()) == 1
        with pytest.raises(ValueError):
            persist_result(s, case, row, CaseResult(**(base | {"status": "failed"})))
    engine.dispose()
