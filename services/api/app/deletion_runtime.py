"""Durable deletion admission and recovery before workers or HTTP data access."""

import fcntl
import hashlib
import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import event, inspect, select
from sqlalchemy.orm import Session

from app import deletion
from app.deletion_lifecycle import erase_purchase, plan_purchase
from app.models import AgentRun, Purchase


class DeletionRuntime:
    def __init__(self, engine, factory):
        self.engine, self.factory = engine, factory
        self.path = self.lineage = None

    def initialize(self):
        database = self.engine.url.database
        if not database or database == ":memory:":
            return
        with self.engine.connect() as connection:
            bound = inspect(connection).has_table(deletion._policy.name)
            if bound:
                rows = connection.execute(select(deletion._policy)).mappings().all()
                if len(rows) != 1:
                    raise deletion.DeletionJournalError("Invalid deletion policy")
                path = rows[0]["journal_path"]
            else:
                # Legacy installations need explicit initialization; never infer
                # an empty deletion history from an already populated database.
                if connection.scalar(select(Purchase.id).limit(1)) is not None:
                    return
                path = str(Path(database).resolve()) + ".deletions.json"
        state = deletion.bind_database(self.engine, path, initialize=not bound)
        self.path, self.lineage = Path(state["journal"]), state["lineage"]
        self.factory.configure(info={"deletion_runtime": self})

    @contextmanager
    def owner(self):
        if self.path is None:
            yield
            return
        descriptor = os.open(str(self.path) + ".worker.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "a+") as stream:
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise deletion.DeletionJournalError("This deletion lineage already has an application worker") from None
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def records(self):
        if self.path is None:
            raise deletion.DeletionJournalError("Deletion unavailable: initialize durable deletion history first")
        return deletion.journal_records(self.path, expected_lineage=self.lineage)

    def reconcile(self):
        if self.path is None:
            return
        with self.factory.begin() as session:
            session.connection().exec_driver_sql("BEGIN IMMEDIATE")
            for identifier in self.records():
                if session.get(Purchase, identifier) is not None:
                    erase_purchase(session, plan_purchase(session, identifier), recovering=True)

    def record(self, purchase):
        self.records()
        fingerprint = hashlib.sha256(purchase.import_key.rsplit(":", 1)[0].encode()).hexdigest()
        deletion.record_deletion(self.path, purchase.id, import_fingerprint=fingerprint,
                                 expected_lineage=self.lineage)


@event.listens_for(Session, "before_flush")
def reject_deleted_writes(session, _context, _instances):
    runtime = session.info.get("deletion_runtime")
    if runtime is None:
        return
    removed = runtime.records()
    if not removed:
        return

    def affected(table, values, visited):
        key = (table.name, values.get("id"))
        if key in visited:
            return False
        visited.add(key)
        if table.name == Purchase.__tablename__:
            return values.get("id") in removed
        if table.name == AgentRun.__tablename__ and removed.intersection(values.get("payload", {}).get("purchase_ids", [])):
            return True
        for column in table.columns:
            for foreign in column.foreign_keys:
                value = values.get(column.key)
                if value is not None:
                    parent = foreign.column.table
                    row = session.execute(select(parent).where(foreign.column == value)).mappings().first()
                    if row is not None and affected(parent, row, visited):
                        return True
        return False

    with session.no_autoflush:
        if any(affected(inspect(type(entity)).local_table,
                        {column.key: getattr(entity, column.key) for column in inspect(type(entity)).columns}, set())
               for entity in [*session.new, *session.dirty]):
            raise deletion.DeletionJournalError("Purchase deletion recorded; stale work cannot recreate its records")
