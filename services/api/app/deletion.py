"""Purchase-local cleanup inside the caller's transaction.

This is not a public deletion API. Its caller must first enforce active-work
guards, handle shared run history, and durably record the deletion intent.
"""

import fcntl
import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import Column, Integer, MetaData, String, Table, delete, inspect, select

_policy_metadata = MetaData()
_policy = Table("purchase_deletion_policy", _policy_metadata,
                Column("id", Integer, primary_key=True), Column("lineage", String, nullable=False),
                Column("journal_path", String, nullable=False))


class DeletionJournalError(ValueError):
    pass


def _valid_identifier(value):
    try:
        return isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        return False


@contextmanager
def _journal_lock(path):
    try:
        fd = os.open(str(path) + ".lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise DeletionJournalError("Deletion journal lock is unavailable") from exc
    with os.fdopen(fd, "a+") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
            raise DeletionJournalError("Deletion journal lock must be a private regular file")
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _valid_fingerprint(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DeletionJournalError("Duplicate fields in deletion history")
        result[key] = value
    return result


def _read_journal(path, expected_lineage=None):
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise DeletionJournalError("Deletion journal must be a private regular file")
            data = json.load(stream, object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DeletionJournalError("Deletion history unavailable; refusing to assume no deletions") from exc
    if (not isinstance(data, dict)
            or set(data) != {"format", "lineage", "authority_path", "sources", "revision", "records"}
            or type(data["format"]) is not int or data["format"] != 2
            or not _valid_identifier(data["lineage"])
            or data["authority_path"] != str(Path(path).resolve())
            or not isinstance(data["sources"], list)
            or not all(_valid_fingerprint(value) for value in data["sources"])
            or len(set(data["sources"])) != len(data["sources"])
            or type(data["revision"]) is not int or data["revision"] < 0
            or not isinstance(data["records"], dict)):
        raise DeletionJournalError("Invalid deletion history; recovery requires the intact journal")
    revisions = []
    for identifier, record in data["records"].items():
        if (not _valid_identifier(identifier) or not isinstance(record, dict)
                or set(record) != {"import_fingerprint", "revision"}
                or not _valid_fingerprint(record["import_fingerprint"])
                or type(record["revision"]) is not int or record["revision"] < 1):
            raise DeletionJournalError("Invalid deletion record; recovery requires the intact journal")
        revisions.append(record["revision"])
    if (len(set(revisions)) != len(revisions) or len(revisions) != data["revision"]
            or max(revisions, default=0) != data["revision"]):
        raise DeletionJournalError("Invalid deletion generation; recovery requires the intact journal")
    if expected_lineage is not None and data["lineage"] != expected_lineage:
        raise DeletionJournalError("Deletion journal belongs to a different database lineage")
    return data


def _publish_journal(path, data):
    fd, name = tempfile.mkstemp(prefix=".deletion-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def initialize_journal(path, *, source_identity=None):
    """Explicit first-install action; never replace existing unreadable history."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with _journal_lock(path):
        if path.exists() or path.is_symlink():
            data = _read_journal(path)
            if source_identity is not None and source_identity not in data["sources"]:
                raise DeletionJournalError("Existing journal is not bound to this source database")
        else:
            if source_identity is not None and not _valid_fingerprint(source_identity):
                raise DeletionJournalError("Expected a source database identity")
            _publish_journal(path, {"format": 2, "lineage": str(uuid4()),
                "authority_path": str(path.resolve()), "sources": [source_identity] if source_identity else [],
                "revision": 0, "records": {}})


def record_deletion(path, identifier, *, import_fingerprint, expected_lineage=None):
    """Durably record intent before purging SQLite; identifiers contain no receipts."""
    if not _valid_identifier(identifier):
        raise DeletionJournalError("Expected a canonical purchase UUID")
    if not _valid_fingerprint(import_fingerprint):
        raise DeletionJournalError("Expected an import-key SHA256 fingerprint")
    path = Path(path)
    with _journal_lock(path):
        data = _read_journal(path, expected_lineage)
        existing = data["records"].get(identifier)
        if existing is not None:
            if existing["import_fingerprint"] != import_fingerprint:
                raise DeletionJournalError("Conflicting fingerprint for an existing deletion")
            return
        data["revision"] += 1
        data["records"][identifier] = {"import_fingerprint": import_fingerprint, "revision": data["revision"]}
        _publish_journal(path, data)


def journal_records(path, *, expected_lineage=None):
    """Read current authoritative history; missing history always fails closed."""
    path = Path(path)
    with _journal_lock(path):
        return frozenset(_read_journal(path, expected_lineage)["records"])


def journal_identity(path):
    path = Path(path)
    with _journal_lock(path):
        return _read_journal(path)["lineage"]


def verify_snapshot_journal(path, source_identity, *, expected_lineage=None):
    """Bind even a pre-policy snapshot to the current authority at its fixed path."""
    path = Path(path)
    with _journal_lock(path):
        data = _read_journal(path, expected_lineage)
        if not _valid_fingerprint(source_identity) or source_identity not in data["sources"]:
            raise DeletionJournalError("Snapshot source does not belong to this deletion journal")
        return data["lineage"]


def bind_database(engine, path, *, initialize=False):
    """Explicit additive install or validation of an existing recovery binding.

    Existing bindings never authorize creating a missing journal. The normal
    startup path must omit initialize; only genuine first installation uses it.
    """
    from app.config import ROOT
    from app.storage import source_identity

    database = engine.url.database
    if not database or database == ":memory:" or engine.dialect.name != "sqlite":
        raise DeletionJournalError("Durable deletion requires an on-disk SQLite database")
    path = Path(path).resolve()
    if path.is_relative_to(ROOT / "apps/web/public"):
        raise DeletionJournalError("Deletion journal must stay outside public web files")
    source = source_identity(database)
    with engine.begin() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        present = inspect(connection).has_table(_policy.name)
        if present:
            columns = {column["name"] for column in inspect(connection).get_columns(_policy.name)}
            if not set(_policy.columns.keys()).issubset(columns):
                raise DeletionJournalError("Incompatible deletion policy; explicit migration required")
            rows = connection.execute(select(_policy)).mappings().all()
            if len(rows) > 1 or (rows and rows[0]["id"] != 1):
                raise DeletionJournalError("Invalid deletion policy; recovery binding is ambiguous")
        else:
            rows = []
        if rows:
            row = rows[0]
            if not _valid_identifier(row["lineage"]):
                raise DeletionJournalError("Invalid database deletion lineage")
            if row["journal_path"] != str(path):
                raise DeletionJournalError("Configured journal differs from the persisted recovery authority")
            with _journal_lock(path):
                data = _read_journal(path, row["lineage"])
                if source not in data["sources"]:
                    data["sources"].append(source)
                    _publish_journal(path, data)
            return {"lineage": row["lineage"], "journal": str(path)}
        if not initialize:
            raise DeletionJournalError("Deletion policy needs explicit first-install initialization")
        initialize_journal(path, source_identity=source)
        lineage = verify_snapshot_journal(path, source)
        if not present:
            _policy.create(connection)
        connection.execute(_policy.insert().values(id=1, lineage=lineage, journal_path=str(path)))
        return {"lineage": lineage, "journal": str(path)}


def reimport_challenge(path, import_fingerprint, *, expected_lineage=None):
    """Current confirmation token; a later deletion invalidates an earlier token."""
    if not _valid_fingerprint(import_fingerprint):
        raise DeletionJournalError("Expected an import-key SHA256 fingerprint")
    path = Path(path)
    with _journal_lock(path):
        data = _read_journal(path, expected_lineage)
        revision = max((record["revision"] for record in data["records"].values()
                        if record["import_fingerprint"] == import_fingerprint), default=0)
        if not revision:
            return None
        return hashlib.sha256(json.dumps([data["lineage"], import_fingerprint, revision]).encode()).hexdigest()


def purge_purchase(session, identifier):
    """Delete a purchase and its foreign-key descendants, never parent runs.

    Reflect the installed schema so optional Diwali/P1 children participate
    without creating tables or disabling SQLite referential integrity.
    The caller owns commit/rollback; no filesystem or provider work occurs.
    """
    return purge_roots(session, "purchases", {identifier})


def purge_roots(session, table_name, identifiers):
    """Erase trusted application roots and FK descendants in this transaction."""
    if not identifiers:
        return {}
    metadata = MetaData()
    metadata.reflect(bind=session.connection())
    root = metadata.tables[table_name]
    present = set(session.scalars(select(root.c.id).where(root.c.id.in_(identifiers))))
    if not present:
        return {}
    selected = {table_name: present}
    changed = True
    while changed:
        changed = False
        for table in metadata.sorted_tables:
            for reference in table.foreign_keys:
                parent_ids = selected.get(reference.column.table.name)
                if not parent_ids:
                    continue
                if reference.column.name != "id" or list(table.primary_key.columns.keys()) != ["id"]:
                    raise ValueError("Unsupported purchase-deletion relationship; no records removed")
                found = set(session.scalars(select(table.c.id).where(reference.parent.in_(parent_ids))))
                known = selected.setdefault(table.name, set())
                if found - known:
                    known.update(found)
                    changed = True
    counts = {}
    for table in reversed(metadata.sorted_tables):
        identifiers = selected.get(table.name)
        if identifiers:
            session.execute(delete(table).where(table.c.id.in_(identifiers)))
            counts[table.name] = len(identifiers)
    return counts


def main():
    """Explicit migration for an existing installation; never reset history."""
    import argparse

    from sqlalchemy import create_engine

    from app.jobs import worker_lock

    parser = argparse.ArgumentParser(description="Initialize durable purchase deletion history")
    parser.add_argument("command", choices=["initialize"])
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    if not args.database.is_file() or args.database.is_symlink():
        parser.error("Expected an existing regular SQLite database")
    engine = create_engine("sqlite:///" + str(args.database.resolve()))
    try:
        with worker_lock(engine):
            if not inspect(engine).has_table("purchases"):
                raise DeletionJournalError("Expected an existing Sueperman database")
            journal = args.journal or Path(str(args.database.resolve()) + ".deletions.json")
            print(json.dumps(bind_database(engine, journal, initialize=True)))
    except (DeletionJournalError, RuntimeError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
