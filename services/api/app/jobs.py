"""Durable intent, single-owner dispatch, and conservative restart recovery.

Only never-claimed jobs may resume. A claimed job is never retried, even when
its lease expires: an external side effect may already have happened.
"""

import asyncio
import fcntl
import hashlib
import json
import os
import string
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values
from sqlalchemy import inspect, select

from app.config import ROOT
from app.models import AgentRun, CollaborationRun

MODELS = (AgentRun, CollaborationRun)
ACTIVE = {"queued", "running", "investigating", "challenging", "building"}


def configuration_digest(settings):
    # Deliberately exclude keys, DSNs, credentials, and their fingerprints.
    values = {key: value for key, value in settings.model_dump().items()
              if key.endswith(("_enabled", "_model", "_seconds", "_per_run", "_per_case"))
              or key in {"demo_mode", "collaboration_public_demo", "diwali_live_authorized",
                         "diwali_operator_demo", "lyzr_review_agent_id", "finch_skill_sha256",
                         "finch_skill_path", "finch_delivery_file", "agent37_instance_id",
                         "band_credentials_file"}}
    if settings.band_enabled:
        if settings.band_credentials_file:
            try:
                path = Path(settings.band_credentials_file)
                if path.stat().st_size > 65536:
                    raise ValueError("Oversized identity file")
                raw = json.loads(path.read_text())
                values["band_identity"] = {"room_id": raw.get("room_id"), "actors": {
                    role: actor.get("agent_id") for role, actor in raw.get("actors", {}).items()}}
            except (OSError, ValueError, TypeError, AttributeError):
                values["band_identity"] = "unavailable"
        else:
            identities = dotenv_values(ROOT / ".env") | dict(os.environ)
            values["band_identity"] = {name: identities.get(name) for name in (
                "BAND_ROOM_ID", "BAND_CONTROLLER_AGENT_ID", "BAND_SCOUT_AGENT_ID",
                "BAND_SKEPTIC_AGENT_ID", "BAND_BUILDER_AGENT_ID")}
    sha = hashlib.sha256(json.dumps(values, sort_keys=True).encode())
    for folder in (ROOT / "services/api/app", ROOT / "demo"):
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix in {".py", ".json", ".csv"}:
                sha.update(str(path.relative_to(ROOT)).encode())
                sha.update(path.read_bytes())
    return sha.hexdigest()


def enqueue(run, settings):
    if run.status in {None, "queued"}:
        run.status = "queued"
        run.payload = run.payload | {"job": {"version": 1, "state": "queued",
            "configuration": configuration_digest(settings), "attempts": 0,
            "recoveries": 0, "queued_at": datetime.now(UTC).isoformat()}}


def recoverable(run):
    job = run.payload.get("job", {})
    if not isinstance(job, dict):
        return False
    try:
        queued_at = datetime.fromisoformat(job.get("queued_at", ""))
    except (ValueError, TypeError):
        return False
    return (run.status == "queued" and type(job.get("version")) is int and job["version"] == 1
            and job.get("state") == "queued" and type(job.get("attempts")) is int and job["attempts"] == 0
            and type(job.get("recoveries")) is int and job["recoveries"] >= 0
            and queued_at.utcoffset() is not None
            and isinstance(job.get("configuration"), str) and len(job["configuration"]) == 64
            and all(char in string.hexdigits for char in job["configuration"])
            and not any(key in job for key in ("owner", "claimed_at", "lease_until", "finished_at")))


def public_job(run):
    job = run.payload.get("job")
    if not isinstance(job, dict):
        return None
    return {"state": job.get("state") if isinstance(job.get("state"), str) else "interrupted",
            **{key: job[key] if type(job.get(key)) is int and job[key] >= 0 else 0
               for key in ("attempts", "recoveries")}}


def interrupt(session, run, reason, state="interrupted"):
    job = run.payload.get("job", {})
    run.status = "partial"
    run.payload = run.payload | {"warnings": [*run.payload.get("warnings", []), reason],
        "job": job | {"state": state, "finished_at": datetime.now(UTC).isoformat()}}
    if isinstance(run, AgentRun) and run.payload.get("collaboration_mode") in {"local", "band"}:
        from app.diwali.persistence import CaseRow, TaskRow
        if not inspect(session.connection()).has_table(CaseRow.__tablename__):
            return
        for task in session.scalars(select(TaskRow).where(TaskRow.run_id == run.id)):
            if task.state != "consumed":
                task.state = "cancelled"
        for case in session.scalars(select(CaseRow).where(CaseRow.run_id == run.id)):
            if case.phase != "DONE":
                case.phase = "DONE"
                case.payload = case.payload | {"failure": "INTERRUPTED"}


def recover(session):
    for model in MODELS:
        for run in session.scalars(select(model)):
            job = run.payload.get("job")
            if "job" in run.payload and not isinstance(job, dict):
                run.payload = run.payload | {"job": {"state": "interrupted", "attempts": 0, "recoveries": 0}}
                if run.status in ACTIVE:
                    interrupt(session, run, "Invalid queued intent; start a new run.")
                continue
            if not job:
                continue
            if recoverable(run):
                run.payload = run.payload | {"job": job | {"recoveries": job.get("recoveries", 0) + 1}}
                if model is CollaborationRun:
                    run.payload = run.payload | {"warnings": list(dict.fromkeys([
                        *run.payload.get("warnings", []), "Queued work recovered after restart."]))}
            elif run.status in ACTIVE:
                interrupt(session, run, "Execution interrupted; external outcome may be unknown. Start a new run.")
            elif job.get("state") == "running":
                run.payload = run.payload | {"job": job | {"state": "finished"}}


@contextmanager
def worker_lock(engine):
    """Reject overlapping application lifespans over one on-disk SQLite DB."""
    path = engine.url.database
    if path in {None, "", ":memory:"}:
        yield
        return
    with Path(path + ".worker.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("This database already has an application worker; run exactly one worker") from None
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def durable(model):
    def decorate(execute):
        @wraps(execute)
        async def dispatch(factory, run_id, settings, *args, **kwargs):
            token = str(uuid4())
            with factory.begin() as session:
                session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                run = session.get(model, run_id)
                if run is None:
                    return
                job = run.payload.get("job")
                # Compatibility for explicitly invoked legacy/test workflows.
                legacy = job is None
                if not legacy:
                    if not recoverable(run):
                        return
                    if job["configuration"] != configuration_digest(settings):
                        interrupt(session, run, "Configuration changed before execution; start a new run.",
                                  "configuration_changed")
                        return
                    for other_model in MODELS:
                        for other in session.scalars(select(other_model).where(other_model.status.in_(ACTIVE))):
                            if (other_model is model and other.id == run_id):
                                continue
                            if other.payload.get("job", {}).get("state") == "running" or other.status != "queued":
                                return
                    from app.p1.monitoring import SourceWatch
                    if (inspect(session.connection()).has_table(SourceWatch.__tablename__)
                            and session.scalar(select(SourceWatch.id).where(SourceWatch.status == "checking"))):
                        return
                    run.payload = run.payload | {"job": job | {"state": "running", "owner": token,
                        "attempts": 1, "claimed_at": datetime.now(UTC).isoformat(),
                        "lease_until": (datetime.now(UTC) + timedelta(seconds=90)).isoformat()}}
            if legacy:
                return await execute(factory, run_id, settings, *args, **kwargs)
            try:
                async with asyncio.timeout(90):
                    return await execute(factory, run_id, settings, *args, **kwargs)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001, S110 -- finally persists sanitized interrupted status
                pass
            finally:
                with factory.begin() as session:
                    session.connection().exec_driver_sql("BEGIN IMMEDIATE")
                    run = session.get(model, run_id)
                    if run is not None and run.payload.get("job", {}).get("owner") == token:
                        if run.status in ACTIVE:
                            interrupt(session, run, "Execution interrupted; external outcome may be unknown. Start a new run.")
                        else:
                            run.payload = run.payload | {"job": run.payload["job"] | {
                                "state": "finished", "finished_at": datetime.now(UTC).isoformat()}}
        return dispatch
    return decorate


async def work_loop(factory, settings, stopped):
    from app.agent.orchestrator import execute as deterministic
    from app.collaboration.controller import execute as team
    from app.diwali.coordinator import execute as collaboration

    while not stopped.is_set():
        pending = []
        with factory() as session:
            for model in MODELS:
                for run in session.scalars(select(model).where(model.status == "queued").order_by(model.created_at)):
                    if recoverable(run):
                        handler = team if model is CollaborationRun else (
                            collaboration if run.payload.get("collaboration_mode", "deterministic") != "deterministic"
                            else deterministic)
                        pending.append((handler, run.id))
        for handler, run_id in pending:
            if stopped.is_set():
                break
            await handler(factory, run_id, settings)
        try:
            await asyncio.wait_for(stopped.wait(), timeout=1)
        except TimeoutError:
            pass
