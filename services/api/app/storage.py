"""Operator-only consistent SQLite snapshots. Never imports the application server."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import sqlite3
import stat
import sys
import tempfile
import threading
from contextlib import closing, contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import monotonic
from typing import cast
from uuid import uuid4

from sqlalchemy import create_engine

from app.config import ROOT
from app.jobs import worker_lock

OWNER = "sueperman-sqlite-snapshot-v1\n"
SNAPSHOT = re.compile(r"snapshot-(\d{8}T\d{12}Z)-[0-9a-f]{32}")


class StorageError(ValueError):
    pass


def utc(value=None):
    value = value or datetime.now(UTC)
    if value.utcoffset() is None:
        raise StorageError("Timezone-aware backup time required")
    return value.astimezone(UTC)


def private_file(path):
    if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise StorageError("Snapshot files must be regular private files")


def private_root(path):
    path = Path(path)
    if path.is_symlink() or path.resolve().is_relative_to(ROOT / "apps/web/public"):
        raise StorageError("Backup directory must be outside the webroot and cannot be a symlink")
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) & 0o077:
        raise StorageError("Backup directory must be private (0700)")
    return path.resolve()


def write_private(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def operation(directory, name=".operation.lock"):
    directory = private_root(directory)
    path = directory / name
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "a") as stream:
        private_file(path)
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StorageError("Another storage operation is active") from None
        try:
            yield directory
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


@contextmanager
def readonly(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise StorageError("Database must be an existing regular file")
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    connection.execute("PRAGMA trusted_schema=OFF")
    try:
        yield connection
    finally:
        connection.close()


def identifier(name):
    return '"' + name.replace('"', '""') + '"'


def describe(connection):
    from app.diwali.persistence import DiwaliBase
    from app.models import Base
    from app.p1 import obligations  # noqa: F401 -- register the additive P1 table
    from app.p1.monitoring import P1Base

    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise StorageError("Database integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise StorageError("Database foreign-key check failed")
    schema = connection.execute("SELECT name,sql FROM sqlite_master WHERE type='table' "
                                "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    tables = {name for name, _sql in schema}
    required = {"purchases", "products", "opportunities", "source_evidence", "eligibility_assessments",
                "claim_packets", "agent_runs", "audit_events"}
    if not required.issubset(tables):
        raise StorageError("Database is not a compatible Sueperman database")
    for metadata in (Base.metadata, DiwaliBase.metadata, P1Base.metadata):
        for name, table in metadata.tables.items():
            if name not in tables:
                continue  # Absent additive tables are created by normal application startup.
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({identifier(name)})")}
            if not set(table.columns.keys()).issubset(columns):
                raise StorageError(f"Incompatible database schema: {name}; explicit migration required")
    for name in ("diwali_schema_versions", "p1_schema_versions"):
        if name in tables and connection.execute(f"SELECT version FROM {identifier(name)}").fetchall() != [(1,)]:
            raise StorageError("Unsupported database schema version; explicit migration required")
    counts = {name: connection.execute(f"SELECT count(*) FROM {identifier(name)}").fetchone()[0]
              for name in sorted(tables)}
    return {"schema_sha256": hashlib.sha256(json.dumps(schema).encode()).hexdigest(), "rows": counts}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_identity(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise StorageError("Source database is unavailable")
    info = path.stat()
    return hashlib.sha256(json.dumps([str(path.resolve()), info.st_dev, info.st_ino]).encode()).hexdigest()


def backup(database, directory, *, now=None, timeout_seconds=120):
    with operation(directory) as root:
        snapshot = _backup(database, root, utc(now), timeout_seconds)
        (root / ".last-error.json").unlink(missing_ok=True)
        sync_directory(root)
        return snapshot


def _backup(database, directory, now, timeout_seconds=120):
    identity = source_identity(database)
    name = f"snapshot-{now.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid4().hex}"
    pending = directory / (".partial-" + name)
    pending.mkdir(mode=0o700)
    destination = directory / name
    try:
        write_private(pending / ".owner", OWNER)
        target = pending / "database.sqlite3"
        write_private(target, "")
        deadline = monotonic() + timeout_seconds
        def progress(_status, _remaining, _total):
            if monotonic() >= deadline:
                raise StorageError("Database snapshot deadline exceeded")
        with readonly(database) as source, closing(sqlite3.connect(target)) as output:
            source.backup(output, pages=64, progress=progress, sleep=0.05)
            output.set_progress_handler(lambda: int(monotonic() >= deadline), 10000)
            output.execute("PRAGMA journal_mode=DELETE")
            description = describe(output)
        with target.open("rb") as stream:
            os.fsync(stream.fileno())
        if source_identity(database) != identity:
            raise StorageError("Source database changed identity during backup")
        manifest = {"format": 1, "id": name, "created_at": now.isoformat(),
                    "source_id": identity, "sha256": digest(target), **description}
        write_private(pending / "manifest.json", json.dumps(manifest, sort_keys=True) + "\n")
        sync_directory(pending)
        pending.rename(destination)
        sync_directory(directory)
        return destination
    finally:
        if pending.exists():
            shutil.rmtree(pending)


def load_snapshot(snapshot):
    snapshot = Path(snapshot)
    match = SNAPSHOT.fullmatch(snapshot.name)
    if (snapshot.is_symlink() or not snapshot.is_dir() or match is None
            or stat.S_IMODE(snapshot.stat().st_mode) & 0o077):
        raise StorageError("Invalid or non-private snapshot directory")
    if {p.name for p in snapshot.iterdir()} != {".owner", "database.sqlite3", "manifest.json"}:
        raise StorageError("Unexpected snapshot files")
    for name in (".owner", "database.sqlite3", "manifest.json"):
        private_file(snapshot / name)
    if (snapshot / ".owner").read_text() != OWNER:
        raise StorageError("Unknown snapshot owner")
    manifest = json.loads((snapshot / "manifest.json").read_text())
    if not isinstance(manifest, dict):
        raise StorageError("Invalid snapshot manifest")
    if (manifest.get("format") != 1 or manifest.get("id") != snapshot.name
            or utc(datetime.fromisoformat(manifest["created_at"])).strftime('%Y%m%dT%H%M%S%fZ')
            != match.group(1)):
        raise StorageError("Invalid snapshot manifest")
    if digest(snapshot / "database.sqlite3") != manifest["sha256"]:
        raise StorageError("Snapshot checksum mismatch")
    with readonly(snapshot / "database.sqlite3") as source:
        description = describe(source)
    if any(manifest.get(key) != value for key, value in description.items()):
        raise StorageError("Snapshot schema or row counts differ from manifest")
    return manifest


def restore(snapshot, database, *, deletion_journal=None):
    snapshot, database = Path(snapshot), Path(database)
    with operation(snapshot.parent):
        manifest = load_snapshot(snapshot)
        database.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        require_new_database(database)
        engine = create_engine("sqlite:///" + str(database.resolve()))
        temporary = None
        try:
            with worker_lock(engine):
                require_new_database(database)
                fd, name = tempfile.mkstemp(prefix=".restore-", dir=database.parent)
                os.close(fd)
                temporary = Path(name)
                shutil.copyfile(snapshot / "database.sqlite3", temporary)
                with reconcile_deletions(temporary, manifest["source_id"], deletion_journal=deletion_journal):
                    reconcile_restore(temporary)
                    with temporary.open("rb") as stream:
                        os.fsync(stream.fileno())
                    # Keep the deletion-authority lock through publication: a new
                    # tombstone cannot land between replay and publishing this file.
                    os.link(temporary, database, follow_symlinks=False)
                    sync_directory(database.parent)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            engine.dispose()
    return database


@contextmanager
def reconcile_deletions(database, source_id, *, deletion_journal=None):
    """Replay the current authority, never a journal rolled back with a snapshot."""
    from sqlalchemy import inspect, select
    from sqlalchemy.orm import Session

    from app import deletion
    from app.deletion_lifecycle import erase_purchase, plan_purchase

    engine = create_engine("sqlite:///" + str(database))
    try:
        with engine.connect() as connection:
            present = inspect(connection).has_table(deletion._policy.name)
            if present:
                columns = {column["name"] for column in inspect(connection).get_columns(deletion._policy.name)}
                if not set(deletion._policy.columns.keys()).issubset(columns):
                    raise StorageError("Incompatible deletion policy; explicit migration required")
                rows = connection.execute(select(deletion._policy)).mappings().all()
                if len(rows) != 1 or rows[0]["id"] != 1 or not deletion._valid_identifier(rows[0]["lineage"]):
                    raise StorageError("Invalid snapshot deletion policy")
                row = rows[0]
                if not isinstance(row["journal_path"], str):
                    raise StorageError("Invalid snapshot deletion authority path")
                path, lineage = Path(row["journal_path"]), row["lineage"]
                if not path.is_absolute() or str(path.resolve()) != row["journal_path"]:
                    raise StorageError("Invalid snapshot deletion authority path")
                if deletion_journal is not None and Path(deletion_journal).resolve() != path:
                    raise StorageError("Explicit journal differs from the snapshot recovery authority")
            else:
                if deletion_journal is None:
                    raise StorageError("Pre-policy snapshot requires --deletion-journal bound to its original source")
                path, lineage = Path(deletion_journal).resolve(), None
        # The journal owns its canonical location and records trusted source
        # identities. An arbitrary empty file cannot authorize an old backup.
        lineage = deletion.verify_snapshot_journal(path, source_id, expected_lineage=lineage)
        with deletion._journal_lock(path):
            data = deletion._read_journal(path, lineage)
            if source_id not in data["sources"]:
                raise StorageError("Snapshot source does not belong to this deletion journal")
            with Session(engine) as session, session.begin():
                session.connection().exec_driver_sql("PRAGMA foreign_keys=ON")
                if not present:
                    deletion._policy.create(session.connection())
                    session.execute(deletion._policy.insert().values(id=1, lineage=lineage, journal_path=str(path)))
                for identifier in data["records"]:
                    erase_purchase(session, plan_purchase(session, identifier, require_purchase=False), recovering=True)
            # Close SQLite before linking its final file. All deletion writes are
            # committed into that file, not a companion WAL that is left behind.
            engine.dispose()
            yield
    finally:
        engine.dispose()


def require_new_database(database):
    paths = [database, *[Path(str(database) + suffix) for suffix in ("-wal", "-shm", "-journal")]]
    if any(path.exists() or path.is_symlink() for path in paths):
        raise StorageError("Restore requires a new database filename without SQLite companions")


def reconcile_restore(database):
    """A historical queue cannot prove what ran after its backup was captured."""
    from sqlalchemy import inspect, select
    from sqlalchemy.orm import Session

    from app import jobs
    from app.models import AgentRun, CollaborationRun
    from app.p1 import monitoring

    engine = create_engine("sqlite:///" + str(database))
    try:
        tables = set(inspect(engine).get_table_names())
        with Session(engine) as session, session.begin():
            for model in (AgentRun, CollaborationRun):
                if model.__tablename__ not in tables:
                    continue
                for row in session.scalars(select(model).where(model.status.in_(jobs.ACTIVE))):
                    run = cast(AgentRun | CollaborationRun, row)
                    if not isinstance(run.payload.get("job", {}), dict):
                        run.payload = run.payload | {"job": {}}
                    jobs.interrupt(session, run,
                        "Restored snapshot: post-backup execution is unknown; start a new run.")
            if monitoring.SourceWatch.__tablename__ in tables:
                monitoring.recover_interrupted(session, utc())
    finally:
        engine.dispose()


def snapshot_time(name):
    match = SNAPSHOT.fullmatch(name.removeprefix(".partial-"))
    try:
        return datetime.strptime(match.group(1), "%Y%m%dT%H%M%S%fZ").replace(tzinfo=UTC) if match else None
    except ValueError:
        return None


def prune(directory, now, *, preserve=None):
    """Only this tool's private, owner-marked, seven-day-old directories expire."""
    removed = 0
    for path in directory.iterdir():
        created = snapshot_time(path.name)
        if (path.name == preserve or created is None or created > now - timedelta(days=7)
                or path.is_symlink() or not path.is_dir()):
            continue
        try:
            private_file(path / ".owner")
            if (path / ".owner").read_text() != OWNER:
                continue
            if any(p.is_symlink() or not p.is_file()
                   or p.name not in {".owner", "manifest.json", "database.sqlite3"}
                   for p in path.iterdir()):
                continue
        except (StorageError, OSError):
            continue
        shutil.rmtree(path)
        removed += 1
    if removed:
        sync_directory(directory)
    return removed


def latest(directory, now, *, source_id=None):
    # A corrupt/incomplete/future snapshot cannot postpone a fresh backup.
    for path in sorted(directory.glob("snapshot-*"), reverse=True):
        try:
            created = snapshot_time(path.name)
            if created is None or created > now:
                continue
            manifest = load_snapshot(path)
            if source_id is not None and manifest.get("source_id") != source_id:
                continue
            return manifest
        except (StorageError, OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            continue
    return None


def status(directory, *, database=None, now=None):
    now, directory = utc(now), private_root(directory)
    identity = source_identity(database) if database is not None else None
    last = latest(directory, now, source_id=identity)
    success = utc(datetime.fromisoformat(last["created_at"])) if last else None
    due_at = success + timedelta(days=1) if success else now
    error = None
    path = directory / ".last-error.json"
    if path.exists():
        private_file(path)
        try:
            failure = json.loads(path.read_text())
            if (not isinstance(failure, dict) or set(failure) != {"at", "error", "source_path"}
                    or not isinstance(failure["at"], str) or not isinstance(failure["error"], str)
                    or not isinstance(failure["source_path"], str) or len(failure["source_path"]) != 64):
                raise ValueError("Malformed scheduler error record")
            selected = (database is None or failure.get("source_path") ==
                        hashlib.sha256(str(Path(database).resolve()).encode()).hexdigest())
            if selected and (success is None or utc(datetime.fromisoformat(failure["at"])) >= success):
                error = failure["error"]
        except (ValueError, TypeError, KeyError):
            error = "Invalid scheduler error record"
    return {"scope": "selected_source" if database is not None else "all_sources",
            "last_success_at": success.isoformat() if success else None,
            "next_due_at": (now if error else due_at).isoformat(), "due": due_at <= now or error is not None,
            "snapshot": last["id"] if last else None, "last_error": error}


def cycle(database, directory, *, now=None):
    now = utc(now)
    with operation(directory) as directory_root:
        try:
            current = status(directory_root, database=database, now=now)
            if not current["due"]:
                removed = prune(directory_root, now, preserve=current["snapshot"])
                return {"state": "not_due", "removed": removed, **current}
            snapshot = _backup(database, directory_root, now)
        except (StorageError, OSError, ValueError, sqlite3.Error) as exc:
            previous = latest(directory_root, now)
            prune(directory_root, now, preserve=previous["id"] if previous else None)
            temporary = directory_root / (".error-" + uuid4().hex)
            write_private(temporary, json.dumps({"at": now.isoformat(), "error": type(exc).__name__,
                "source_path": hashlib.sha256(str(Path(database).resolve()).encode()).hexdigest()}) + "\n")
            temporary.replace(directory_root / ".last-error.json")
            sync_directory(directory_root)
            raise
        removed = prune(directory_root, now, preserve=snapshot.name)
        (directory_root / ".last-error.json").unlink(missing_ok=True)
        sync_directory(directory_root)
        return {"state": "created", "snapshot": str(snapshot), "removed": removed}


def schedule(database, directory, *, poll_seconds=60):
    if not 1 <= poll_seconds <= 3600:
        raise StorageError("Scheduler poll interval must be between 1 and 3600 seconds")
    stopped = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_args: stopped.set())
    with operation(directory, ".scheduler.lock"):
        while not stopped.is_set():
            try:
                print(json.dumps(cycle(database, directory)), flush=True)
            except (StorageError, OSError, ValueError, sqlite3.Error) as exc:
                print("Backup cycle failed: " + type(exc).__name__, file=sys.stderr, flush=True)
            stopped.wait(poll_seconds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("backup", "restore", "cycle", "schedule", "status"):
        sub = commands.add_parser(command)
        sub.add_argument("--database", type=Path, required=command != "status")
        sub.add_argument("--snapshot" if command == "restore" else "--directory", type=Path, required=True)
        if command == "schedule":
            sub.add_argument("--poll-seconds", type=float, default=60)
        if command == "restore":
            sub.add_argument("--deletion-journal", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            print(json.dumps({"snapshot": str(backup(args.database, args.directory))}))
        elif args.command == "restore":
            print(json.dumps({"database": str(restore(args.snapshot, args.database,
                                                     deletion_journal=args.deletion_journal))}))
        elif args.command == "cycle":
            print(json.dumps(cycle(args.database, args.directory)))
        elif args.command == "status":
            result = status(args.directory, database=args.database)
            print(json.dumps(result))
            return int(result["due"] or result["last_error"] is not None)
        else:
            schedule(args.database, args.directory, poll_seconds=args.poll_seconds)
    except (StorageError, OSError, sqlite3.Error, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print("Storage operation failed: " + (str(exc) if isinstance(exc, StorageError) else type(exc).__name__),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
