"""Persist recovery identity without touching the user's running database."""

import shutil

import pytest


def binding():
    from app import deletion

    assert callable(getattr(deletion, "bind_database", None)), "Database/journal binding is not implemented"
    return deletion


def test_bound_database_reopens_with_same_history_and_rejects_another_journal(tmp_path):
    implementation = binding()
    from app.db import database

    source, journal = tmp_path / "source.db", tmp_path / "deletions.json"
    engine, _factory = database(f"sqlite:///{source}")
    try:
        state = implementation.bind_database(engine, journal, initialize=True)
        implementation.record_deletion(journal, "7ca730ca-f462-4a80-a170-37df73e90681",
                                       import_fingerprint="a" * 64, expected_lineage=state["lineage"])
        assert implementation.bind_database(engine, journal) == state
        wrong = tmp_path / "wrong.json"
        implementation.initialize_journal(wrong)
        with pytest.raises(implementation.DeletionJournalError):
            implementation.bind_database(engine, wrong, initialize=True)
        assert implementation.journal_records(journal, expected_lineage=state["lineage"]) == {
            "7ca730ca-f462-4a80-a170-37df73e90681"}
    finally:
        engine.dispose()


def test_missing_history_is_not_reinitialized_even_with_install_flag(tmp_path):
    implementation = binding()
    from app.db import database

    engine, _factory = database(f"sqlite:///{tmp_path / 'source.db'}")
    journal = tmp_path / "deletions.json"
    try:
        implementation.bind_database(engine, journal, initialize=True)
        journal.unlink()
        for initialize in [False, True]:
            with pytest.raises(implementation.DeletionJournalError):
                implementation.bind_database(engine, journal, initialize=initialize)
            assert not journal.exists()
    finally:
        engine.dispose()


def test_old_snapshot_source_can_be_verified_but_unrelated_empty_history_cannot(tmp_path):
    implementation = binding()
    from app.db import database
    from app.storage import source_identity

    source = tmp_path / "source.db"
    engine, _factory = database(f"sqlite:///{source}")
    try:
        previous_snapshot_source = source_identity(source)
        journal = tmp_path / "deletions.json"
        state = implementation.bind_database(engine, journal, initialize=True)
        assert implementation.verify_snapshot_journal(journal, previous_snapshot_source) == state["lineage"]
        wrong = tmp_path / "wrong.json"
        implementation.initialize_journal(wrong)
        with pytest.raises(implementation.DeletionJournalError):
            implementation.verify_snapshot_journal(wrong, previous_snapshot_source)
        with pytest.raises(implementation.DeletionJournalError):
            implementation.verify_snapshot_journal(journal, "0" * 64)
        duplicate = tmp_path / "duplicate.json"
        shutil.copyfile(journal, duplicate)
        duplicate.chmod(0o600)
        with pytest.raises(implementation.DeletionJournalError):
            implementation.verify_snapshot_journal(duplicate, previous_snapshot_source)
    finally:
        engine.dispose()


def test_missing_lineage_in_malformed_policy_cannot_disable_binding(tmp_path):
    implementation = binding()
    from app.db import database

    engine, _factory = database(f"sqlite:///{tmp_path / 'source.db'}")
    journal = tmp_path / "deletions.json"
    implementation.initialize_journal(journal)
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE purchase_deletion_policy (id INTEGER PRIMARY KEY, lineage TEXT, journal_path TEXT)")
            connection.exec_driver_sql("INSERT INTO purchase_deletion_policy VALUES (1,NULL,?)", (str(journal.resolve()),))
        with pytest.raises(implementation.DeletionJournalError):
            implementation.bind_database(engine, journal)
    finally:
        engine.dispose()


def test_journal_cannot_be_installed_inside_public_web_files(tmp_path, monkeypatch):
    implementation = binding()
    from app import config
    from app.db import database

    monkeypatch.setattr(config, "ROOT", tmp_path)
    engine, _factory = database(f"sqlite:///{tmp_path / 'source.db'}")
    journal = tmp_path / "apps/web/public/deletions.json"
    try:
        with pytest.raises(implementation.DeletionJournalError):
            implementation.bind_database(engine, journal, initialize=True)
        assert not journal.exists()
    finally:
        engine.dispose()
