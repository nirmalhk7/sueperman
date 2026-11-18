"""Purchase lifecycle at the real HTTP and SQLite boundaries."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    monkeypatch.setenv("P1_ENABLED", "true")
    from app.main import create_app

    with TestClient(create_app(f"sqlite:///{tmp_path / 'purchases.db'}")) as app:
        yield app


def upload(client, order):
    content = (
        "order_id,purchased_at,merchant,product_name,brand,model_number\n"
        f"{order},2024-06-12,Synthetic shop,Portable Power Bank,NEWDERY,ZHX-PB22\n"
    ).encode()
    response = client.post("/api/uploads/purchases", files={"file": ("purchases.csv", content, "text/csv")})
    response.raise_for_status()
    return response.json()


def test_confirmed_deletion_removes_purchase_without_touching_other_imports_or_demo(client):
    seed = client.post("/api/demo/reset").json()
    removed, kept = upload(client, "REMOVE-ME"), upload(client, "KEEP-ME")
    identifier = removed["purchase_ids"][0]
    response = client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True})
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    products = client.get("/api/products").json()
    assert {p["id"] for p in products} == {*seed["product_ids"], *kept["product_ids"]}
    assert client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True}).status_code == 200


def test_missing_confirmation_never_deletes_purchase(client):
    imported = upload(client, "CONFIRM-FIRST")
    identifier = imported["purchase_ids"][0]
    for body in [{}, {"confirmed": False}]:
        assert client.post(f"/api/purchases/{identifier}/delete", json=body).status_code == 422
    assert imported["product_ids"][0] in {p["id"] for p in client.get("/api/products").json()}


def test_cross_origin_request_cannot_delete_purchase(client):
    imported = upload(client, "ORIGIN-CHECK")
    response = client.post(f"/api/purchases/{imported['purchase_ids'][0]}/delete",
                          json={"confirmed": True}, headers={"Origin": "https://untrusted.invalid"})
    assert response.status_code == 403
    assert imported["product_ids"][0] in {p["id"] for p in client.get("/api/products").json()}


def test_shared_history_requires_preview_and_separate_confirmation(client, tmp_path):
    from sqlalchemy import select

    from app.db import database
    from app.models import AgentRun, Opportunity, Purchase

    removed, kept = upload(client, "SHARED-REMOVE"), upload(client, "SHARED-KEEP")
    run = client.post("/api/runs", json={"mode": "demo",
        "purchase_ids": removed["purchase_ids"] + kept["purchase_ids"], "idempotency_key": "shared-history"})
    run.raise_for_status()
    identifier = removed["purchase_ids"][0]
    preview = client.get(f"/api/purchases/{identifier}/deletion-preview")
    assert preview.status_code == 200
    assert preview.json()["shared_investigations"] == 1
    assert client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True}).status_code == 409
    response = client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True,
        "expected_binding": preview.json()["binding"], "shared_history_confirmed": True})
    assert response.status_code == 200
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        with factory() as session:
            assert session.get(Purchase, identifier) is None
            assert session.get(Purchase, kept["purchase_ids"][0]) is not None
            assert session.get(AgentRun, run.json()["run_id"]) is None
            opportunity = session.scalar(select(Opportunity).where(Opportunity.product_id == kept["product_ids"][0]))
            assert opportunity is not None
            other_id = opportunity.id
        assert client.get(f"/api/opportunities/{other_id}").status_code == 200
    finally:
        engine.dispose()


def test_changed_preview_cannot_authorize_new_shared_history(client):
    removed, kept = upload(client, "PREVIEW-REMOVE"), upload(client, "PREVIEW-KEEP")
    identifier = removed["purchase_ids"][0]
    preview = client.get(f"/api/purchases/{identifier}/deletion-preview")
    assert preview.status_code == 200
    client.post("/api/runs", json={"mode": "demo",
        "purchase_ids": removed["purchase_ids"] + kept["purchase_ids"],
        "idempotency_key": "after-preview"}).raise_for_status()
    response = client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True,
        "expected_binding": preview.json()["binding"], "shared_history_confirmed": True})
    assert response.status_code == 409
    assert removed["product_ids"][0] in {p["id"] for p in client.get("/api/products").json()}


def test_pending_deletion_is_reconciled_before_serving_purchases(client, tmp_path):
    from app import deletion
    from app.db import database
    from app.models import Purchase

    imported = upload(client, "INTENT-ONLY")
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        with factory() as session:
            purchase = session.get(Purchase, imported["purchase_ids"][0])
            import hashlib

            fingerprint = hashlib.sha256(purchase.import_key.rsplit(":", 1)[0].encode()).hexdigest()
        path = tmp_path / "purchases.db.deletions.json"
        deletion.record_deletion(path, imported["purchase_ids"][0], import_fingerprint=fingerprint)
        assert client.get("/api/products").json() == []
    finally:
        engine.dispose()


def test_active_investigation_blocks_deletion_without_recording_intent(client, tmp_path):
    from app import deletion
    from app.db import database
    from app.models import AgentRun

    imported = upload(client, "ACTIVE")
    identifier = imported["purchase_ids"][0]
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        with factory.begin() as session:
            session.add(AgentRun(idempotency_key="active", status="running", demo=False,
                                 payload={"purchase_ids": [identifier]}))
        assert client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True}).status_code == 409
        assert identifier not in deletion.journal_records(tmp_path / "purchases.db.deletions.json")
    finally:
        engine.dispose()


def test_legacy_database_requires_explicit_history_installation(tmp_path, monkeypatch):
    import os
    import subprocess
    import sys

    from app.db import database
    from app.main import create_app
    from app.models import Purchase

    path = tmp_path / "legacy.db"
    engine, factory = database(f"sqlite:///{path}")
    with factory.begin() as session:
        purchase = Purchase(import_key="csv:" + "a" * 64 + ":0", demo=False, payload={})
        session.add(purchase)
        session.flush()
        identifier = purchase.id
    engine.dispose()
    with TestClient(create_app(f"sqlite:///{path}")) as client:
        assert client.get(f"/api/purchases/{identifier}/deletion-preview").status_code == 503
    result = subprocess.run([sys.executable, "-m", "app.deletion", "initialize", "--database", str(path)],
                            env=os.environ | {"PYTHONPATH": "services/api"}, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    with TestClient(create_app(f"sqlite:///{path}")) as client:
        assert client.get(f"/api/purchases/{identifier}/deletion-preview").status_code == 200


def test_failed_sql_cleanup_keeps_intent_and_rejects_delayed_admission(client, monkeypatch):
    from app import deletion
    from app.api import purchases
    from app.models import AgentRun, Purchase

    imported = upload(client, "FAILED-PURGE")
    identifier = imported["purchase_ids"][0]
    runtime = client.app.state.deletion_runtime
    def fail_cleanup(*_args):
        raise RuntimeError("injected SQLite cleanup failure")
    monkeypatch.setattr(purchases, "erase_purchase", fail_cleanup)
    with pytest.raises(RuntimeError, match="injected SQLite cleanup failure"):
        client.post(f"/api/purchases/{identifier}/delete", json={"confirmed": True})
    assert identifier in runtime.records()
    with runtime.factory() as session:
        assert session.get(Purchase, identifier) is not None
    with pytest.raises(deletion.DeletionJournalError), runtime.factory.begin() as session:
        session.add(AgentRun(idempotency_key="delayed-after-intent", status="queued",
                             payload={"purchase_ids": [identifier]}))
    assert client.get("/api/products").json() == []


def test_pending_intent_blocks_delayed_source_watch_write(client):
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app import deletion
    from app.models import Opportunity, Purchase
    from app.p1.monitoring import SourceWatch, set_watch

    imported = upload(client, "DELAYED-WATCH")
    client.post("/api/runs", json={"mode": "demo", "purchase_ids": imported["purchase_ids"],
                                 "idempotency_key": "delayed-watch"}).raise_for_status()
    runtime = client.app.state.deletion_runtime
    with runtime.factory.begin() as session:
        opportunity = session.scalar(select(Opportunity))
        watch = set_watch(session, opportunity.id, enabled=True, observed_at=datetime.now(UTC))
        session.flush()
        watch_id = watch.id
    with runtime.factory() as session:
        runtime.record(session.get(Purchase, imported["purchase_ids"][0]))
    with pytest.raises(deletion.DeletionJournalError), runtime.factory.begin() as session:
        watch = session.get(SourceWatch, watch_id)
        watch.status = "checking"


def test_restart_applies_pending_intent_before_queued_work(tmp_path):
    from app.main import create_app
    from app.models import AgentRun, Purchase

    url = f"sqlite:///{tmp_path / 'restart.db'}"
    first = create_app(url)
    with TestClient(first) as client:
        imported = upload(client, "RESTART")
        runtime = first.state.deletion_runtime
        with runtime.factory.begin() as session:
            run = AgentRun(idempotency_key="never-started", status="queued",
                           payload={"purchase_ids": imported["purchase_ids"]})
            session.add(run)
            session.flush()
            run_id = run.id
        with runtime.factory() as session:
            runtime.record(session.get(Purchase, imported["purchase_ids"][0]))
    second = create_app(url)
    with TestClient(second) as client:
        assert client.get("/api/products").json() == []
        assert client.get(f"/api/runs/{run_id}").status_code == 404


def test_history_cleanup_keeps_other_findings_and_requires_new_check_for_old_draft(client, tmp_path):
    import importlib

    from sqlalchemy import select

    from app.db import database
    from app.models import AgentRun, AuditEvent, ClaimPacket, Opportunity, Product, Purchase

    removed, kept = upload(client, "GRAPH-REMOVE"), upload(client, "GRAPH-KEEP")
    run = client.post("/api/runs", json={"mode": "demo",
        "purchase_ids": removed["purchase_ids"] + kept["purchase_ids"], "idempotency_key": "graph-history"}).json()
    try:
        implementation = importlib.import_module("app.deletion_lifecycle")
    except ModuleNotFoundError:
        implementation = None
    assert callable(getattr(implementation, "plan_purchase", None)), "Linked-history deletion plan is not implemented"
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        with factory.begin() as session:
            plan = implementation.plan_purchase(session, removed["purchase_ids"][0])
            assert plan.public()["shared_investigations"] == 1
            implementation.erase_purchase(session, plan)
        with factory() as session:
            assert session.get(Purchase, removed["purchase_ids"][0]) is None
            assert session.get(Product, removed["product_ids"][0]) is None
            assert session.get(AgentRun, run["run_id"]) is None
            assert session.scalar(select(AuditEvent).where(AuditEvent.run_id == run["run_id"])) is None
            other = session.scalar(select(Opportunity).where(Opportunity.product_id == kept["product_ids"][0]))
            assert other is not None
            draft = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == other.id))
            assert draft.payload["status"] == "needs_evidence"
            assert draft.payload["approved_at"] is None
            assert session.get(Purchase, kept["purchase_ids"][0]) is not None
            packet_id = draft.id
        blocked = client.post(f"/api/claim-packets/{packet_id}/export")
        assert blocked.status_code == 409
        assert "history" in blocked.json()["message"].lower()
    finally:
        engine.dispose()


def test_history_cleanup_preserves_newer_independent_finding_and_approval(client, tmp_path):
    import importlib

    from sqlalchemy import select

    from app.db import database
    from app.models import ClaimPacket, Opportunity

    removed, kept = upload(client, "NEWER-REMOVE"), upload(client, "NEWER-KEEP")
    client.post("/api/runs", json={"mode": "demo", "purchase_ids": removed["purchase_ids"] + kept["purchase_ids"],
                                 "idempotency_key": "old-shared"}).raise_for_status()
    client.post("/api/runs", json={"mode": "demo", "purchase_ids": kept["purchase_ids"],
                                 "idempotency_key": "new-independent"}).raise_for_status()
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        with factory() as session:
            other = session.scalar(select(Opportunity).where(Opportunity.product_id == kept["product_ids"][0]))
            packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == other.id))
            packet_id, other_id = packet.id, other.id
        approved = client.post(f"/api/claim-packets/{packet_id}/approve-local", json={"confirmed": True}).raise_for_status().json()
        implementation = importlib.import_module("app.deletion_lifecycle")
        with factory.begin() as session:
            implementation.erase_purchase(session, implementation.plan_purchase(session, removed["purchase_ids"][0]))
        with factory() as session:
            assert not session.get(Opportunity, other_id).payload.get("stale", False)
            from datetime import datetime

            assert datetime.fromisoformat(session.get(ClaimPacket, packet_id).payload["approved_at"]) == datetime.fromisoformat(approved["approved_at"])
        assert client.post(f"/api/claim-packets/{packet_id}/export").status_code == 200
    finally:
        engine.dispose()


def test_partial_shared_run_missing_final_membership_invalidates_dependent_draft(client, tmp_path):
    from sqlalchemy import select

    from app.db import database
    from app.deletion_lifecycle import erase_purchase, plan_purchase
    from app.models import AgentRun, ClaimPacket, Opportunity

    removed, kept = upload(client, "PARTIAL-REMOVE"), upload(client, "PARTIAL-KEEP")
    response = client.post("/api/runs", json={"mode": "demo", "purchase_ids": removed["purchase_ids"] + kept["purchase_ids"],
                                            "idempotency_key": "partial-shared"}).json()
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        # Persisted interruption boundary: findings committed before the final
        # run membership update. Recovery marks the incomplete run partial.
        with factory.begin() as session:
            run = session.get(AgentRun, response["run_id"])
            run.status = "partial"
            run.payload = run.payload | {"opportunities": []}
        with factory.begin() as session:
            erase_purchase(session, plan_purchase(session, removed["purchase_ids"][0]))
        with factory() as session:
            other = session.scalar(select(Opportunity).where(Opportunity.product_id == kept["product_ids"][0]))
            packet = session.scalar(select(ClaimPacket).where(ClaimPacket.opportunity_id == other.id))
            assert other.payload.get("stale") is True
            assert packet.payload["status"] == "needs_evidence"
    finally:
        engine.dispose()


def test_purchase_purge_removes_linked_findings_packets_and_cases_only(client, tmp_path):
    """Catches incomplete child cleanup or deleting another purchase's findings."""
    from importlib import import_module

    from sqlalchemy import select

    from app.db import database
    from app.models import CaseRecord, ClaimPacket, Opportunity, Product, Purchase

    seeded = client.post("/api/demo/reset").json()
    removed = {key: [seeded[key][0]] for key in ["purchase_ids", "product_ids"]}
    kept = upload(client, "PURGE-KEPT")
    for item in [removed, kept]:
        response = client.post("/api/runs", json={"mode": "demo", "purchase_ids": item["purchase_ids"],
                                                "idempotency_key": item["purchase_ids"][0]})
        response.raise_for_status()
    response = client.post("/api/collaborations", json={"product_ids": removed["product_ids"],
                                                       "mode": "replay", "idempotency_key": "purge-team"})
    response.raise_for_status()
    try:
        module = import_module("app.deletion")
    except ModuleNotFoundError:
        module = None
    purge = getattr(module, "purge_purchase", None)
    assert callable(purge), "Purchase-dependent record purge is not implemented"
    engine, factory = database(f"sqlite:///{tmp_path / 'purchases.db'}")
    try:
        with factory.begin() as session:
            purge(session, removed["purchase_ids"][0])
        with factory() as session:
            assert session.get(Purchase, removed["purchase_ids"][0]) is None
            assert session.get(Product, removed["product_ids"][0]) is None
            assert session.scalar(select(CaseRecord).where(CaseRecord.product_id == removed["product_ids"][0])) is None
            opportunities = session.scalars(select(Opportunity)).all()
            assert {item.product_id for item in opportunities} == set(kept["product_ids"])
            assert session.scalar(select(ClaimPacket)) is not None
            assert session.get(Purchase, kept["purchase_ids"][0]) is not None
    finally:
        engine.dispose()
