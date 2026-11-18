"""Exercise backup/restore at the operator CLI and real database boundary."""

import json
import os
import sqlite3
import stat
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[4]


def cli(*args):
    return subprocess.run([sys.executable, "-m", "app.storage", *map(str, args)],
        cwd=ROOT, env=os.environ | {"PYTHONPATH": str(ROOT / "services/api"), "SENTRY_DSN": ""},
        capture_output=True, text=True, timeout=20, check=False)


def rows(path):
    with sqlite3.connect(path) as db:
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
        return {name: sorted(db.execute('SELECT * FROM "' + name.replace('"', '""') + '"').fetchall(), key=repr)
                for (name,) in tables}


@pytest.fixture
def app_lifecycles():
    with ExitStack() as stack:
        yield stack


@pytest.fixture
def populated(tmp_path, monkeypatch, app_lifecycles):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    monkeypatch.setenv("P1_ENABLED", "true")
    from app.main import create_app
    path = tmp_path / "source.db"
    client = app_lifecycles.enter_context(TestClient(create_app(f"sqlite:///{path}")))
    seed = client.post("/api/demo/reset").json()
    run = client.post("/api/runs", json={"mode": "demo", "purchase_ids": seed["purchase_ids"],
        "idempotency_key": "storage-fixture"}).json()
    cases = client.get("/api/opportunities", params={"run_id": run["run_id"]}).json()
    exact = next(c for c in cases if c["status"] == "verified_match")
    packet = client.post(f"/api/opportunities/{exact['id']}/claim-packet").json()
    endpoint = f"/api/claim-packets/{packet['id']}"
    client.post(endpoint + "/approve-local", json={"confirmed": True}).raise_for_status()
    exported = client.post(endpoint + "/export").raise_for_status().text
    product = client.get("/api/products").json()[0]
    team = client.post("/api/collaborations", json={"product_ids": [product["id"]],
        "mode": "replay", "idempotency_key": "storage-team"}).json()
    assert client.get(f"/api/collaborations/{team['id']}").json()["status"] == "ready_for_review"
    # Keep WAL open and committed: a plain file copy could miss these rows.
    with sqlite3.connect(path) as writer:
        writer.execute("PRAGMA wal_autocheckpoint=0")
        writer.execute("INSERT INTO receipt_ocr_usage(day,calls) VALUES ('2026-11-17',7)")
        writer.commit()
        yield path, client, endpoint, exported


def test_snapshot_copies_committed_wal_and_restores_all_rows(populated, tmp_path, app_lifecycles):
    source, _client, endpoint, expected_export = populated
    (source.parent / ".env.private").write_text("PRIVATE_TOKEN=must-not-be-backed-up")
    directory = tmp_path / "backups"
    expected = rows(source)
    result = cli("backup", "--database", source, "--directory", directory)
    assert result.returncode == 0, result.stderr
    snapshot = Path(json.loads(result.stdout)["snapshot"])
    assert snapshot.parent == directory
    assert sorted(p.name for p in snapshot.iterdir()) == [".owner", "database.sqlite3", "manifest.json"]
    assert stat.S_IMODE(snapshot.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(p.stat().st_mode) == 0o600 for p in snapshot.iterdir())
    assert rows(snapshot / "database.sqlite3") == expected
    restored = tmp_path / "restored.db"
    result = cli("restore", "--snapshot", snapshot, "--database", restored)
    assert result.returncode == 0, result.stderr
    assert rows(restored) == expected
    assert rows(source) == expected
    assert stat.S_IMODE(restored.stat().st_mode) == 0o600
    # Recovery keeps the journal lineage; only one app may own that lineage.
    app_lifecycles.close()
    from app.main import create_app
    with TestClient(create_app(f"sqlite:///{restored}")) as client:
        assert client.post(endpoint + "/export").raise_for_status().text == expected_export
        assert len(client.get("/api/products").json()) == 5
        with sqlite3.connect(restored) as db:
            assert db.execute("SELECT calls FROM receipt_ocr_usage WHERE day='2026-11-17'").fetchone() == (7,)


def test_invalid_source_does_not_publish_snapshot_or_touch_other_files(tmp_path):
    source = tmp_path / "invalid.db"
    source.write_bytes(b"not a sqlite database")
    backups = tmp_path / "backups"
    result = cli("backup", "--database", source, "--directory", backups)
    assert result.returncode != 0
    assert source.read_bytes() == b"not a sqlite database"
    assert not backups.exists() or not list(backups.glob("snapshot-*"))


def test_restore_refuses_overwrite_and_corrupt_snapshot(populated, tmp_path):
    source, _client, _endpoint, _exported = populated
    result = cli("backup", "--database", source, "--directory", tmp_path / "backups")
    assert result.returncode == 0, result.stderr
    snapshot = Path(json.loads(result.stdout)["snapshot"])
    existing = tmp_path / "existing.db"
    existing.write_bytes(b"must remain unchanged")
    assert cli("restore", "--snapshot", snapshot, "--database", existing).returncode != 0
    assert existing.read_bytes() == b"must remain unchanged"
    data = snapshot / "database.sqlite3"
    with data.open("ab") as stream:
        stream.write(b"tampering")
    target = tmp_path / "corrupt-restored.db"
    assert cli("restore", "--snapshot", snapshot, "--database", target).returncode != 0
    assert not target.exists()


def cycle(database, directory, now):
    from app import storage
    implementation = getattr(storage, "cycle", None)
    assert callable(implementation), "Persistent daily backup cycle is not implemented"
    return implementation(database, directory, now=now)


def test_daily_schedule_survives_new_invocation_and_reports_status(populated, tmp_path):
    from datetime import UTC, datetime, timedelta
    source, _client, _endpoint, _export = populated
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    directory = tmp_path / "backups"
    first = cycle(source, directory, now)
    assert first["state"] == "created"
    assert cycle(source, directory, now + timedelta(hours=23))["state"] == "not_due"
    assert cycle(source, directory, now + timedelta(days=1))["state"] == "created"
    assert len(list(directory.glob("snapshot-*"))) == 2
    result = cli("status", "--directory", directory)
    assert result.returncode in {0, 1}, result.stderr
    assert json.loads(result.stdout)["last_success_at"]


def test_seven_day_retention_only_prunes_owned_snapshots(populated, tmp_path):
    from datetime import UTC, datetime, timedelta

    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    now = datetime(2026, 11, 1, 12, tzinfo=UTC)
    snapshots = [storage.backup(source, directory, now=now + timedelta(days=i)) for i in range(9)]
    foreign = directory / "operator-notes"
    foreign.mkdir()
    (foreign / "keep").write_text("unrelated file")
    result = cycle(source, directory, now + timedelta(days=8, hours=1))
    assert result["state"] == "not_due"
    assert not snapshots[0].exists() and not snapshots[1].exists()
    assert all(p.exists() for p in snapshots[2:])
    assert (foreign / "keep").read_text() == "unrelated file"


def test_corrupt_or_future_snapshot_cannot_postpone_backup(populated, tmp_path):
    from datetime import UTC, datetime, timedelta

    from app import storage
    source, _client, _endpoint, _export = populated
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    directory = tmp_path / "backups"
    future = storage.backup(source, directory, now=now + timedelta(days=365))
    current = storage.backup(source, directory, now=now - timedelta(hours=1))
    with (current / "database.sqlite3").open("ab") as stream:
        stream.write(b"corruption")
    result = cycle(source, directory, now)
    assert result["state"] == "created"
    assert Path(result["snapshot"]) not in {current, future}


def test_source_missing_and_legacy_schema_are_not_silently_created_or_changed(populated, tmp_path):
    source, _client, _endpoint, _export = populated
    missing = tmp_path / "missing.db"
    assert cli("backup", "--database", missing, "--directory", tmp_path / "missing-backups").returncode == 2
    assert not missing.exists()
    legacy = tmp_path / "legacy.db"
    # Build a separate incompatible historical schema, preserving the original current database.
    with sqlite3.connect(source) as origin, sqlite3.connect(legacy) as copy:
        origin.backup(copy)
        copy.execute("DROP TABLE collaboration_tasks")
        copy.execute("CREATE TABLE collaboration_tasks(id TEXT PRIMARY KEY, obsolete_payload TEXT)")
        copy.commit()
    expected = rows(legacy)
    result = cli("backup", "--database", legacy, "--directory", tmp_path / "legacy-backups")
    assert result.returncode == 2
    assert "explicit migration required" in result.stderr
    assert rows(legacy) == expected


def test_nonprivate_or_symlink_backup_locations_and_restore_companions_are_refused(populated, tmp_path):
    source, _client, _endpoint, _export = populated
    public = tmp_path / "public-backups"
    public.mkdir(mode=0o755)
    assert cli("backup", "--database", source, "--directory", public).returncode == 2
    link = tmp_path / "linked-backups"
    link.symlink_to(public, target_is_directory=True)
    assert cli("backup", "--database", source, "--directory", link).returncode == 2
    result = cli("backup", "--database", source, "--directory", tmp_path / "private")
    assert result.returncode == 0
    snapshot = Path(json.loads(result.stdout)["snapshot"])
    destination = tmp_path / "restored.db"
    Path(str(destination) + "-wal").write_bytes(b"orphaned committed data")
    assert cli("restore", "--snapshot", snapshot, "--database", destination).returncode == 2
    assert not destination.exists()
    assert Path(str(destination) + "-wal").read_bytes() == b"orphaned committed data"


def test_malformed_generated_name_cannot_disable_backup_schedule(populated, tmp_path):
    from datetime import UTC, datetime

    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    directory.mkdir(mode=0o700)
    invalid = directory / ("snapshot-99999999T999999999999Z-" + "a" * 32)
    invalid.mkdir(mode=0o700)
    (invalid / ".owner").write_text(storage.OWNER)
    assert cycle(source, directory, datetime(2026, 11, 17, 12, tzinfo=UTC))["state"] == "created"
    assert invalid.exists()


def test_failed_snapshot_publication_leaves_no_visible_backup_and_original_unchanged(populated, tmp_path, monkeypatch):
    from app import storage
    source, _client, _endpoint, _export = populated
    expected = rows(source)
    original = Path.rename
    def fail_publish(path, target):
        if path.name.startswith(".partial-"):
            raise OSError("controlled publication failure")
        return original(path, target)
    monkeypatch.setattr(Path, "rename", fail_publish)
    directory = tmp_path / "backups"
    with pytest.raises(OSError, match="controlled publication"):
        storage.backup(source, directory)
    assert not list(directory.glob("snapshot-*"))
    assert not list(directory.glob(".partial-*"))
    assert rows(source) == expected


def test_backup_deadline_does_not_publish_partial_snapshot(populated, tmp_path):
    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    with pytest.raises(storage.StorageError, match="deadline"):
        storage.backup(source, directory, timeout_seconds=0)
    assert not list(directory.glob("snapshot-*"))


def test_schedule_process_restart_does_not_duplicate_daily_backup(populated, tmp_path):
    import time
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    command = [sys.executable, "-m", "app.storage", "schedule", "--database", str(source),
               "--directory", str(directory), "--poll-seconds", "1"]
    env = os.environ | {"PYTHONPATH": str(ROOT / "services/api"), "SENTRY_DSN": ""}
    for attempt in range(2):
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 10
            while not list(directory.glob("snapshot-*")):
                assert process.poll() is None
                assert time.monotonic() < deadline
                time.sleep(0.05)
            if attempt == 1:
                time.sleep(1.25)
        finally:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == 0, (stdout, stderr)
        assert len(list(directory.glob("snapshot-*"))) == 1
    result = cli("status", "--directory", directory)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["due"] is False


def test_snapshot_failure_is_reported_without_postponing_retry(populated, tmp_path):
    from datetime import UTC, datetime

    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    with pytest.raises(storage.StorageError):
        cycle(tmp_path / "missing.db", directory, now)
    before = storage.status(directory, now=now)
    assert before["due"] is True and before["last_error"] == "StorageError"
    assert cycle(source, directory, now)["state"] == "created"
    after = storage.status(directory, now=now)
    assert after["due"] is False and after["last_error"] is None


def test_retention_never_recurses_into_unexpected_artifacts(populated, tmp_path):
    from datetime import UTC, datetime, timedelta

    from app import storage
    source, _client, _endpoint, _export = populated
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    directory = tmp_path / "backups"
    old = storage.backup(source, directory, now=now - timedelta(days=8))
    (old / "database.sqlite3").unlink()
    unexpected = old / "database.sqlite3"
    unexpected.mkdir()
    (unexpected / "operator-file").write_text("keep unrelated data")
    cycle(source, directory, now)
    assert (unexpected / "operator-file").is_file(), "Retention deleted an unexpected nested artifact"
    assert (unexpected / "operator-file").read_text() == "keep unrelated data"


def test_racing_restores_publish_only_one_complete_new_database(populated, tmp_path):
    source, _client, _endpoint, _export = populated
    result = cli("backup", "--database", source, "--directory", tmp_path / "backups")
    assert result.returncode == 0
    snapshot = Path(json.loads(result.stdout)["snapshot"])
    destination = tmp_path / "restore-once.db"
    command = [sys.executable, "-m", "app.storage", "restore", "--snapshot", str(snapshot),
               "--database", str(destination)]
    env = os.environ | {"PYTHONPATH": str(ROOT / "services/api"), "SENTRY_DSN": ""}
    processes = [subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True) for _ in range(2)]
    for process in processes:
        process.communicate(timeout=20)
    assert sorted(p.returncode for p in processes) == [0, 2]
    assert rows(destination) == rows(snapshot / "database.sqlite3")


def test_switching_database_cannot_reuse_another_sources_daily_success(populated, tmp_path):
    from contextlib import closing
    from datetime import UTC, datetime, timedelta

    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    first = cycle(source, directory, now)
    other = tmp_path / "other.db"
    with closing(sqlite3.connect(source)) as origin, closing(sqlite3.connect(other)) as output:
        origin.backup(output)
        output.execute("UPDATE receipt_ocr_usage SET calls=9")
        output.commit()
    result = cycle(other, directory, now + timedelta(hours=1))
    assert result["state"] == "created", "Another database's backup postponed the selected database"
    assert result["snapshot"] != first["snapshot"]
    assert rows(Path(result["snapshot"]) / "database.sqlite3")["receipt_ocr_usage"] == [("2026-11-17", 9)]
    assert storage.status(directory, database=other, now=now + timedelta(hours=2))["snapshot"] == Path(result["snapshot"]).name


def test_backup_outage_preserves_last_valid_recovery_copy(populated, tmp_path):
    from datetime import UTC, datetime, timedelta

    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    old = storage.backup(source, directory, now=now - timedelta(days=8))
    with pytest.raises(storage.StorageError):
        cycle(tmp_path / "missing.db", directory, now)
    assert old.is_dir(), "Source failure deleted the last valid recovery copy"
    assert cycle(source, directory, now)["state"] == "created"
    assert not old.exists()


def test_restored_queue_cannot_repeat_work_executed_after_backup(populated, tmp_path, app_lifecycles):
    import asyncio
    from contextlib import closing

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app import deletion, jobs
    from app.agent.orchestrator import execute
    from app.config import Settings
    from app.models import AgentRun, Purchase
    source, _client, _endpoint, _export = populated
    isolated = tmp_path / "isolated.db"
    with closing(sqlite3.connect(source)) as origin, closing(sqlite3.connect(isolated)) as output:
        origin.backup(output)
    engine = create_engine(f"sqlite:///{isolated}")
    deletion.bind_database(engine, _client.app.state.deletion_runtime.path)
    from sqlalchemy.orm import sessionmaker
    factory = sessionmaker(engine, expire_on_commit=False)
    with Session(engine) as session, session.begin():
        purchase_ids = list(session.scalars(select(Purchase.id)))
        run = AgentRun(idempotency_key="after-snapshot", demo=True, payload={"purchase_ids": purchase_ids,
            "mode": "demo", "summary": {}, "warnings": [], "provider_modes": {}, "opportunities": []})
        jobs.enqueue(run, Settings())
        session.add(run)
        session.flush()
        identifier = run.id
    directory = tmp_path / "backups"
    result = cli("backup", "--database", isolated, "--directory", directory)
    assert result.returncode == 0, result.stderr
    asyncio.run(execute(factory, identifier, Settings()))
    with Session(engine) as session:
        assert session.get(AgentRun, identifier).status == "completed"
    engine.dispose()
    destination = tmp_path / "from-old-snapshot.db"
    snapshot = Path(json.loads(result.stdout)["snapshot"])
    assert cli("restore", "--snapshot", snapshot, "--database", destination).returncode == 0
    app_lifecycles.close()
    from app.main import create_app
    with TestClient(create_app(f"sqlite:///{destination}")) as client:
        restored = client.get(f"/api/runs/{identifier}").json()
        assert restored["status"] == "partial", "Restore replayed work with an unknown post-snapshot outcome"
        assert restored["job"]["attempts"] == 0
        assert "snapshot" in " ".join(restored["warnings"]).lower()
        assert client.get(f"/api/runs/{identifier}/events").json() == []


def test_restore_of_inflight_source_check_revokes_only_related_approval(populated, tmp_path, app_lifecycles):
    from contextlib import closing
    from datetime import UTC, datetime

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app import deletion
    from app.models import Opportunity
    from app.p1 import monitoring
    source, _client, endpoint, _export = populated
    isolated = tmp_path / "checking-source.db"
    with closing(sqlite3.connect(source)) as origin, closing(sqlite3.connect(isolated)) as output:
        origin.backup(output)
    engine = create_engine(f"sqlite:///{isolated}")
    deletion.bind_database(engine, _client.app.state.deletion_runtime.path)
    with Session(engine) as session, session.begin():
        opportunity = session.scalar(select(Opportunity).where(Opportunity.payload["status"].as_string() == "verified_match"))
        watch = monitoring.set_watch(session, opportunity.id, enabled=True, observed_at=datetime.now(UTC))
        watch.status, watch.lease = "checking", "interrupted-source-call"
        session.flush()
        watch_id = watch.id
    engine.dispose()
    result = cli("backup", "--database", isolated, "--directory", tmp_path / "backups")
    assert result.returncode == 0, result.stderr
    destination = tmp_path / "restored-check.db"
    result = cli("restore", "--snapshot", json.loads(result.stdout)["snapshot"], "--database", destination)
    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite:///{destination}")
    with Session(engine) as session:
        watch = session.get(monitoring.SourceWatch, watch_id)
        assert watch.enabled and watch.status == "interrupted" and watch.lease is None
    engine.dispose()
    app_lifecycles.close()
    from app.main import create_app
    with TestClient(create_app(f"sqlite:///{destination}")) as client:
        assert client.post(endpoint + "/export").status_code == 409
    assert rows(source)["claim_packets"] != rows(destination)["claim_packets"]


def test_existing_live_database_is_refused_with_controlled_error(populated, tmp_path):
    source, _client, _endpoint, _export = populated
    result = cli("backup", "--database", source, "--directory", tmp_path / "backups")
    assert result.returncode == 0
    expected = rows(source)
    result = cli("restore", "--snapshot", json.loads(result.stdout)["snapshot"], "--database", source)
    assert result.returncode == 2, result.stderr
    assert rows(source) == expected


def test_failure_for_another_source_does_not_poison_selected_backup_status(populated, tmp_path):
    from datetime import UTC, datetime, timedelta

    from app import storage
    source, _client, _endpoint, _export = populated
    now = datetime(2026, 11, 17, 12, tzinfo=UTC)
    directory = tmp_path / "backups"
    cycle(source, directory, now)
    with pytest.raises(storage.StorageError):
        cycle(tmp_path / "other-missing.db", directory, now + timedelta(hours=1))
    state = storage.status(directory, database=source, now=now + timedelta(hours=2))
    assert state["due"] is False and state["last_error"] is None


def test_malformed_error_record_cannot_stop_due_backup(populated, tmp_path):
    from datetime import UTC, datetime

    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    directory.mkdir(mode=0o700)
    storage.write_private(directory / ".last-error.json", "[]")
    assert cycle(source, directory, datetime(2026, 11, 17, 12, tzinfo=UTC))["state"] == "created"


def test_successful_manual_backup_clears_previous_error_state(populated, tmp_path):
    from app import storage
    source, _client, _endpoint, _export = populated
    directory = tmp_path / "backups"
    directory.mkdir(mode=0o700)
    storage.write_private(directory / ".last-error.json", "[]")
    storage.backup(source, directory)
    state = storage.status(directory, database=source)
    assert state["due"] is False and state["last_error"] is None


def test_restore_rejects_checksum_valid_but_incompatible_historical_schema(populated, tmp_path):
    import hashlib
    from contextlib import closing
    source, _client, _endpoint, _export = populated
    result = cli("backup", "--database", source, "--directory", tmp_path / "backups")
    assert result.returncode == 0
    snapshot = Path(json.loads(result.stdout)["snapshot"])
    database = snapshot / "database.sqlite3"
    with closing(sqlite3.connect(database)) as db:
        db.execute("DROP TABLE collaboration_tasks")
        db.execute("CREATE TABLE collaboration_tasks(id TEXT PRIMARY KEY, obsolete_payload TEXT)")
        db.commit()
        schema = db.execute("SELECT name,sql FROM sqlite_master WHERE type='table' "
                            "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    manifest_file = snapshot / "manifest.json"
    manifest = json.loads(manifest_file.read_text())
    with database.open("rb") as stream:
        manifest["sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    manifest["schema_sha256"] = hashlib.sha256(json.dumps(schema).encode()).hexdigest()
    manifest["rows"] = {name: len(values) for name, values in rows(database).items()}
    manifest_file.write_text(json.dumps(manifest))
    destination = tmp_path / "old-runtime.db"
    result = cli("restore", "--snapshot", snapshot, "--database", destination)
    assert result.returncode == 2
    assert "explicit migration required" in result.stderr
    assert not destination.exists()
