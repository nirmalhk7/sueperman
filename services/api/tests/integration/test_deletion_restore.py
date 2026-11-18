"""Deletion intent must survive recovery from an older SQLite snapshot."""

import sqlite3

import pytest

from app import deletion, storage
from app.db import database
from app.models import AgentRun, AuditEvent, Product, Purchase


@pytest.fixture
def deletion_snapshot(tmp_path):
    source = tmp_path / "source.db"
    engine, factory = database(f"sqlite:///{source}")
    journal = tmp_path / "deletions.json"
    state = deletion.bind_database(engine, journal, initialize=True)
    with factory.begin() as session:
        removed = Purchase(import_key="csv:" + "a" * 64 + ":0", payload={})
        kept = Purchase(import_key="csv:" + "b" * 64 + ":0", payload={})
        session.add_all([removed, kept])
        session.flush()
        removed_id, kept_id = removed.id, kept.id
        session.add_all([Product(purchase_id=removed_id, payload={}), Product(purchase_id=kept_id, payload={})])
        run = AgentRun(idempotency_key="deleted-history", status="completed",
                       payload={"purchase_ids": [removed_id], "opportunities": []})
        session.add(run)
        session.flush()
        session.add(AuditEvent(run_id=run.id, seq=1, payload={"purchase": removed_id}))
        run_id = run.id
    snapshot = storage.backup(source, tmp_path / "backups")
    deletion.record_deletion(journal, removed_id, import_fingerprint="c" * 64,
                             expected_lineage=state["lineage"])
    yield source, snapshot, journal, removed_id, kept_id, run_id
    engine.dispose()


def test_restore_reapplies_current_deletions_before_publishing_database(deletion_snapshot, tmp_path):
    source, snapshot, _journal, removed_id, kept_id, run_id = deletion_snapshot
    restored = storage.restore(snapshot, tmp_path / "restored.db")
    with sqlite3.connect(restored) as connection:
        assert connection.execute("SELECT id FROM purchases").fetchall() == [(kept_id,)]
        assert connection.execute("SELECT purchase_id FROM products").fetchall() == [(kept_id,)]
        assert connection.execute("SELECT id FROM agent_runs WHERE id=?", (run_id,)).fetchall() == []
        assert connection.execute("SELECT id FROM audit_events").fetchall() == []
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    # Recovery alters only the candidate; neither source nor historical backup is rewritten.
    for original in [source, snapshot / "database.sqlite3"]:
        with sqlite3.connect(original) as connection:
            assert connection.execute("SELECT id FROM purchases WHERE id=?", (removed_id,)).fetchone() == (removed_id,)


@pytest.mark.parametrize("failure", ["missing", "corrupt", "different_lineage"])
def test_unavailable_deletion_authority_never_publishes_restore(deletion_snapshot, tmp_path, failure):
    _source, snapshot, journal, _removed, _kept, _run = deletion_snapshot
    journal.unlink()
    if failure == "corrupt":
        journal.write_text("{}")
        journal.chmod(0o600)
    elif failure == "different_lineage":
        deletion.initialize_journal(journal)
    target = tmp_path / "must-not-exist.db"
    with pytest.raises(ValueError):
        storage.restore(snapshot, target)
    assert not target.exists()
    assert not list(tmp_path.glob(".restore-*"))


def test_prepolicy_snapshot_requires_verified_explicit_journal(tmp_path):
    source = tmp_path / "legacy-source.db"
    engine, factory = database(f"sqlite:///{source}")
    try:
        with factory.begin() as session:
            purchase = Purchase(import_key="csv:legacy:0", payload={})
            session.add(purchase)
            session.flush()
            identifier = purchase.id
        snapshot = storage.backup(source, tmp_path / "legacy-backups")
        journal = tmp_path / "legacy-deletions.json"
        state = deletion.bind_database(engine, journal, initialize=True)
        deletion.record_deletion(journal, identifier, import_fingerprint="d" * 64,
                                 expected_lineage=state["lineage"])
        with pytest.raises(ValueError):
            storage.restore(snapshot, tmp_path / "unbound.db")
        assert not (tmp_path / "unbound.db").exists()
        wrong = tmp_path / "unrelated.json"
        deletion.initialize_journal(wrong)
        with pytest.raises(ValueError):
            storage.restore(snapshot, tmp_path / "wrong.db", deletion_journal=wrong)
        assert not (tmp_path / "wrong.db").exists()
        restored = storage.restore(snapshot, tmp_path / "legacy-restored.db", deletion_journal=journal)
        with sqlite3.connect(restored) as connection:
            assert connection.execute("SELECT id FROM purchases").fetchall() == []
            assert connection.execute("SELECT lineage,journal_path FROM purchase_deletion_policy").fetchall() == [
                (state["lineage"], str(journal.resolve()))]
    finally:
        engine.dispose()


def test_malformed_snapshot_policy_fails_closed_with_operator_error(tmp_path):
    source = tmp_path / "malformed.db"
    engine, _factory = database(f"sqlite:///{source}")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE purchase_deletion_policy(id INTEGER PRIMARY KEY,lineage TEXT,journal_path TEXT)")
            connection.exec_driver_sql("INSERT INTO purchase_deletion_policy VALUES (1,?,NULL)",
                                      ("7ca730ca-f462-4a80-a170-37df73e90681",))
        snapshot = storage.backup(source, tmp_path / "malformed-backups")
        with pytest.raises(storage.StorageError, match="authority path"):
            storage.restore(snapshot, tmp_path / "malformed-restored.db")
        assert not (tmp_path / "malformed-restored.db").exists()
    finally:
        engine.dispose()
