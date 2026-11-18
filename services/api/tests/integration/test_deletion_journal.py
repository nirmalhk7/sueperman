"""Deletion intent must outlive database restore and process restart."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

FIRST = "7ca730ca-f462-4a80-a170-37df73e90681"
SECOND = "cce1ca1e-b237-48ca-8134-6613e416275c"
FINGERPRINT = "a" * 64


def journal():
    from app import deletion

    for name in ["initialize_journal", "record_deletion", "journal_records"]:
        assert callable(getattr(deletion, name, None)), "Durable deletion journal is not implemented"
    return deletion


def test_record_survives_another_process_and_repeated_intent_is_idempotent(tmp_path):
    implementation = journal()
    path = tmp_path / "deletions.json"
    implementation.initialize_journal(path)
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    code = "import json,sys;from app.deletion import journal_records;print(json.dumps(sorted(journal_records(sys.argv[1]))))"
    result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True,
                            text=True, timeout=10, check=False,
                            env=os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[2])})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [FIRST]
    assert path.stat().st_mode & 0o777 == 0o600


def test_missing_or_corrupt_journal_never_becomes_an_empty_deletion_history(tmp_path):
    implementation = journal()
    path = tmp_path / "deletions.json"
    with pytest.raises(implementation.DeletionJournalError):
        implementation.journal_records(path)
    with pytest.raises(implementation.DeletionJournalError):
        implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    assert not path.exists()
    path.write_text("unreadable deletion history")
    path.chmod(0o600)
    for operation in [implementation.initialize_journal,
                      lambda p: implementation.record_deletion(p, FIRST, import_fingerprint=FINGERPRINT), implementation.journal_records]:
        with pytest.raises(implementation.DeletionJournalError):
            operation(path)
        assert path.read_text() == "unreadable deletion history"


def test_failed_publication_preserves_previous_deletions_and_cleans_temporary_file(tmp_path, monkeypatch):
    implementation = journal()
    path = tmp_path / "deletions.json"
    implementation.initialize_journal(path)
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    before = path.read_bytes()

    def fail_replace(*args, **kwargs):
        raise OSError("simulated unavailable storage")

    with monkeypatch.context() as patch:
        patch.setattr(implementation.os, "replace", fail_replace)
        with pytest.raises(OSError, match="simulated unavailable storage"):
            implementation.record_deletion(path, SECOND, import_fingerprint=FINGERPRINT)
    assert path.read_bytes() == before
    assert implementation.journal_records(path) == frozenset({FIRST})
    assert {p.name for p in tmp_path.iterdir()} == {"deletions.json", "deletions.json.lock"}


def test_symlink_journal_cannot_overwrite_another_file(tmp_path):
    implementation = journal()
    other = tmp_path / "unrelated.json"
    other.write_text("keep unchanged")
    path = tmp_path / "deletions.json"
    path.symlink_to(other)
    with pytest.raises(implementation.DeletionJournalError):
        implementation.initialize_journal(path)
    assert other.read_text() == "keep unchanged"


def test_fifo_journal_is_rejected_without_waiting_for_a_writer(tmp_path):
    journal()
    path = tmp_path / "deletions.json"
    os.mkfifo(path, 0o600)
    code = (
        "import sys;from app.deletion import journal_records,DeletionJournalError\n"
        "try: journal_records(sys.argv[1])\n"
        "except DeletionJournalError: print('refused')\n"
    )
    result = subprocess.run([sys.executable, "-c", code, str(path)], capture_output=True,
                            text=True, timeout=2, check=False,
                            env=os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[2])})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "refused"


def test_concurrent_writers_preserve_every_confirmed_deletion(tmp_path):
    implementation = journal()
    path = tmp_path / "deletions.json"
    implementation.initialize_journal(path)
    code = "import sys;from app.deletion import record_deletion;record_deletion(sys.argv[1],sys.argv[2],import_fingerprint=sys.argv[3])"
    processes = [subprocess.Popen([sys.executable, "-c", code, str(path), identifier, FINGERPRINT],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env=os.environ | {"PYTHONPATH": str(Path(__file__).resolve().parents[2])})
                 for identifier in [FIRST, SECOND, FIRST, SECOND]]
    for process in processes:
        _stdout, stderr = process.communicate(timeout=10)
        assert process.returncode == 0, stderr
    assert implementation.journal_records(path) == frozenset({FIRST, SECOND})


def test_reimport_confirmation_changes_when_the_same_import_is_deleted_again(tmp_path):
    implementation = journal()
    challenge = getattr(implementation, "reimport_challenge", None)
    assert callable(challenge), "Generation-bound re-import confirmation is not implemented"
    path = tmp_path / "deletions.json"
    implementation.initialize_journal(path)
    assert challenge(path, FINGERPRINT) is None
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    first = challenge(path, FINGERPRINT)
    assert isinstance(first, str) and first
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    assert challenge(path, FINGERPRINT) == first
    implementation.record_deletion(path, SECOND, import_fingerprint=FINGERPRINT)
    assert challenge(path, FINGERPRINT) != first
    assert challenge(path, "b" * 64) is None


def test_wrong_empty_journal_cannot_satisfy_expected_database_lineage(tmp_path):
    implementation = journal()
    identity = getattr(implementation, "journal_identity", None)
    assert callable(identity), "Database-lineage verification is not implemented"
    first, wrong = tmp_path / "first.json", tmp_path / "wrong.json"
    implementation.initialize_journal(first)
    implementation.initialize_journal(wrong)
    expected = identity(first)
    assert identity(wrong) != expected
    with pytest.raises(implementation.DeletionJournalError):
        implementation.journal_records(wrong, expected_lineage=expected)
    assert implementation.journal_records(first, expected_lineage=expected) == frozenset()
    implementation.initialize_journal(first)
    assert identity(first) == expected


def test_duplicate_json_keys_cannot_erase_deletion_history(tmp_path):
    implementation = journal()
    path = tmp_path / "deletions.json"
    implementation.initialize_journal(path)
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    data = json.loads(path.read_text())
    data["revision"] = 0
    path.write_text(json.dumps(data)[:-1] + ',"records":{}}')
    with pytest.raises(implementation.DeletionJournalError):
        implementation.journal_records(path)


def test_missing_earlier_deletion_cannot_be_hidden_by_later_generation(tmp_path):
    implementation = journal()
    path = tmp_path / "deletions.json"
    implementation.initialize_journal(path)
    implementation.record_deletion(path, FIRST, import_fingerprint=FINGERPRINT)
    implementation.record_deletion(path, SECOND, import_fingerprint=FINGERPRINT)
    data = json.loads(path.read_text())
    del data["records"][FIRST]
    path.write_text(json.dumps(data))
    with pytest.raises(implementation.DeletionJournalError):
        implementation.journal_records(path)
