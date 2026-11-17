"""Durable admission survives process loss without repeating started work."""

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from fastapi import BackgroundTasks
from fastapi.testclient import TestClient
from sqlalchemy.orm.attributes import flag_modified

from app.db import database
from app.main import create_app
from app.models import AgentRun, CollaborationRun, Product


def admit_without_dispatch(tmp_path, monkeypatch, mode):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    monkeypatch.setattr(BackgroundTasks, "add_task", lambda *args, **kwargs: None)
    url = f"sqlite:///{tmp_path}/recover.db"
    # No lifespan: simulate losing the process after admission commits, before dispatch.
    client = TestClient(create_app(url))
    seed = client.post("/api/demo/reset").json()
    if mode == "team":
        product = client.get("/api/products").json()[0]
        endpoint = "/api/collaborations"
        body = {"product_ids": [product["id"]], "idempotency_key": "durable", "mode": "replay"}
    else:
        endpoint = "/api/runs"
        body = {"purchase_ids": seed["purchase_ids"], "idempotency_key": "durable",
                "mode": "demo", "collaboration_mode": mode}
    response = client.post(endpoint, json=body)
    assert response.status_code == 200, response.text
    run_id = response.json().get("run_id", response.json().get("id"))
    client.close()
    return url, endpoint, run_id


@pytest.mark.parametrize("mode", ["deterministic", "local", "team"])
def test_restart_executes_unclaimed_durable_intent_once(tmp_path, monkeypatch, mode):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, mode)
    with TestClient(create_app(url)) as client:
        deadline = time.monotonic() + 4
        while True:
            result = client.get(f"{endpoint}/{run_id}").json()
            if result["status"] not in {"queued", "running", "investigating", "building", "challenging"}:
                break
            assert time.monotonic() < deadline, result
            time.sleep(0.02)
        assert result["status"] in {"completed", "ready_for_review"}, result
        assert result["job"]["recoveries"] == 1
        assert result["job"]["attempts"] == 1
        assert result["job"]["state"] == "finished"
        if mode == "team":
            assert "Queued work recovered after restart." in result["warnings"]
        events = client.get(f"{endpoint}/{run_id}/events").json()
    with TestClient(create_app(url)) as client:
        assert client.get(f"{endpoint}/{run_id}/events").json() == events
        assert client.get(f"{endpoint}/{run_id}").json()["job"]["attempts"] == 1


@pytest.mark.parametrize("mode", ["deterministic", "local", "team"])
def test_restart_never_repeats_claimed_job(tmp_path, monkeypatch, mode):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, mode)
    engine, factory = database(url)
    model = CollaborationRun if mode == "team" else AgentRun
    with factory.begin() as session:
        row = session.get(model, run_id)
        row.payload = row.payload | {"job": row.payload.get("job", {}) | {
            "state": "running", "attempts": 1, "owner": "lost-process",
            "lease_until": "2000-01-01T00:00:00+00:00"}}
    engine.dispose()
    with TestClient(create_app(url)) as client:
        result = client.get(f"{endpoint}/{run_id}").json()
        assert result["status"] == "partial", result
        assert result["job"]["state"] == "interrupted"
        assert result["job"]["attempts"] == 1
        assert "new run" in " ".join(result["warnings"]).lower()


@pytest.mark.parametrize("setting,value", [("OPENAI_ENABLED", "true"),
    ("LYZR_REVIEW_AGENT_ID", "different-reviewer"), ("FINCH_SKILL_SHA256", "b" * 64),
    ("AGENT37_INSTANCE_ID", "different-instance")])
def test_recovery_refuses_changed_provider_configuration(tmp_path, monkeypatch, setting, value):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    monkeypatch.setenv(setting, value)
    with TestClient(create_app(url)) as client:
        deadline = time.monotonic() + 4
        while True:
            result = client.get(f"{endpoint}/{run_id}").json()
            if result["status"] != "queued":
                break
            assert time.monotonic() < deadline
            time.sleep(0.02)
        assert result["status"] == "partial"
        assert result["job"]["attempts"] == 0
        assert result["job"]["state"] == "configuration_changed"


@pytest.mark.parametrize("bad_job", [[], "invalid", {"version": 1, "state": "queued"}])
def test_malformed_intent_cannot_crash_startup_or_execute(tmp_path, monkeypatch, bad_job):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    engine, factory = database(url)
    with factory.begin() as session:
        row = session.get(AgentRun, run_id)
        row.payload = row.payload | {"job": bad_job}
    engine.dispose()
    with TestClient(create_app(url)) as client:
        result = client.get(f"{endpoint}/{run_id}").json()
        assert result["status"] == "partial"
        assert client.get(f"{endpoint}/{run_id}/events").json() == []


def test_second_application_worker_cannot_recover_live_execution(tmp_path, monkeypatch):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    with TestClient(create_app(url)) as client:
        with pytest.raises(RuntimeError, match="already has an application worker"), TestClient(create_app(url)):
            pass
        assert client.get(f"{endpoint}/{run_id}").status_code == 200


@pytest.mark.parametrize("field,value", [("recoveries", "bad"), ("recoveries", -1),
    ("attempts", False), ("queued_at", "not-a-date"), ("configuration", "z" * 64)])
def test_invalid_nested_intent_is_partial_without_startup_failure(tmp_path, monkeypatch, field, value):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    engine, factory = database(url)
    with factory.begin() as session:
        run = session.get(AgentRun, run_id)
        run.payload = run.payload | {"job": run.payload["job"] | {field: value}}
        # JSON equality treats False == 0; force the corrupted shape to reach SQLite.
        flag_modified(run, "payload")
    engine.dispose()
    with TestClient(create_app(url)) as client:
        result = client.get(f"{endpoint}/{run_id}").json()
        assert result["status"] == "partial"
        assert client.get(f"{endpoint}/{run_id}/events").json() == []


@pytest.mark.parametrize("stage", ["claimed", "effect", "terminal"])
def test_process_exit_does_not_repeat_claim_or_external_effect(tmp_path, monkeypatch, stage):
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    script = '''
import asyncio,os,sys
from pathlib import Path
from app import jobs
from app.config import Settings
from app.db import database
from app.models import AgentRun
url,identifier,effect,stage=sys.argv[1:]
engine,factory=database(url)
@jobs.durable(AgentRun)
async def execute(factory,identifier,settings):
    if stage=="claimed": os._exit(9)
    with open(effect,"a") as stream:
        stream.write("effect\\n"); stream.flush(); os.fsync(stream.fileno())
    if stage=="terminal":
        with factory.begin() as session: session.get(AgentRun,identifier).status="completed"
    os._exit(9)
asyncio.run(execute(factory,identifier,Settings()))
'''
    effect = tmp_path / "external-effect.txt"
    result = subprocess.run([sys.executable, "-c", script, url, run_id, str(effect), stage],
        env=os.environ | {"SENTRY_DSN": "", "PYTHONPATH": str(Path(__file__).resolve().parents[2])},
        capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 9, result.stderr
    before = effect.read_text() if effect.exists() else ""
    assert before == ("" if stage == "claimed" else "effect\n")
    with TestClient(create_app(url)) as client:
        run = client.get(f"{endpoint}/{run_id}").json()
        assert run["status"] == ("completed" if stage == "terminal" else "partial")
        assert run["job"]["attempts"] == 1
        assert set(run["job"]) == {"state", "attempts", "recoveries"}
    assert (effect.read_text() if effect.exists() else "") == before


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [None, "exception", "cancel"])
async def test_racing_delivery_and_uncertain_outcome_never_repeat_effect(tmp_path, monkeypatch, failure):
    from app import jobs
    from app.config import Settings

    url, _endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    engine, factory = database(url)
    effect = tmp_path / "effects.txt"

    @jobs.durable(AgentRun)
    async def execute(factory, identifier, settings):
        with effect.open("a") as stream:
            stream.write("external effect\n")
        await asyncio.sleep(0)
        if failure == "cancel":
            raise asyncio.CancelledError
        if failure == "exception":
            raise RuntimeError("private provider response")
        with factory.begin() as session:
            session.get(AgentRun, identifier).status = "completed"

    await asyncio.gather(execute(factory, run_id, Settings()), execute(factory, run_id, Settings()),
                         return_exceptions=True)
    await execute(factory, run_id, Settings())
    assert effect.read_text() == "external effect\n"
    with factory() as session:
        run = session.get(AgentRun, run_id)
        assert run.status == ("partial" if failure else "completed")
        assert run.payload["job"]["attempts"] == 1
        assert "private provider response" not in str(run.payload)
    engine.dispose()


def test_team_answer_revision_survives_admission_restart(tmp_path, monkeypatch):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    url = f"sqlite:///{tmp_path}/answer.db"
    client = TestClient(create_app(url))
    client.post("/api/demo/reset")
    product = next(p for p in client.get("/api/products").json() if not p["product"]["model_number"])
    first = client.post("/api/collaborations", json={"product_ids": [product["id"]],
        "mode": "replay", "idempotency_key": "question"}).json()
    before = client.get(f"/api/collaborations/{first['id']}").json()
    assert before["status"] == "needs_information"
    monkeypatch.setattr(BackgroundTasks, "add_task", lambda *args, **kwargs: None)
    answer = client.post(f"/api/collaborations/{first['id']}/answers", json={
        "revision": before["revision"], "field": "model_number", "value": "ZHX-PB22",
        "confirmed": True, "idempotency_key": "answer"})
    assert answer.status_code == 200, answer.text
    identifier = answer.json()["id"]
    client.close()
    with TestClient(create_app(url)) as client:
        deadline = time.monotonic() + 4
        while True:
            run = client.get(f"/api/collaborations/{identifier}").json()
            if run["status"] == "ready_for_review":
                break
            assert time.monotonic() < deadline, run
            time.sleep(0.02)
        assert run["job"]["attempts"] == 1
        assert run["job"]["recoveries"] == 1


@pytest.mark.asyncio
async def test_timeout_leaves_partial_and_never_repeats_claim(tmp_path, monkeypatch):
    from app import jobs
    from app.config import Settings

    url, _endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    engine, factory = database(url)
    timeout = asyncio.timeout
    def accelerated_timeout(seconds):
        assert seconds == 90
        return timeout(0.01)
    monkeypatch.setattr(jobs.asyncio, "timeout", accelerated_timeout)
    effect = tmp_path / "started"
    @jobs.durable(AgentRun)
    async def execute(factory, identifier, settings):
        effect.write_text("one attempt")
        await asyncio.sleep(1)
        pytest.fail("Execution exceeded its deadline")
    await execute(factory, run_id, Settings())
    await execute(factory, run_id, Settings())
    with factory() as session:
        run = session.get(AgentRun, run_id)
        assert run.status == "partial"
        assert run.payload["job"]["attempts"] == 1
    assert effect.read_text() == "one attempt"
    engine.dispose()


def test_changed_application_bytes_block_recovery(tmp_path, monkeypatch):
    from app import jobs
    root = tmp_path / "source"
    code = root / "services/api/app/rule.py"
    code.parent.mkdir(parents=True)
    code.write_text("rule version one")
    monkeypatch.setattr(jobs, "ROOT", root)
    url, endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    code.write_text("rule version two")
    with TestClient(create_app(url)) as client:
        deadline = time.monotonic() + 4
        while True:
            run = client.get(f"{endpoint}/{run_id}").json()
            if run["status"] != "queued":
                break
            assert time.monotonic() < deadline
            time.sleep(0.02)
        assert run["status"] == "partial"
        assert run["job"]["state"] == "configuration_changed"
        assert run["job"]["attempts"] == 0


@pytest.mark.asyncio
async def test_execution_claim_excludes_other_run_types(tmp_path, monkeypatch):
    from sqlalchemy import select

    from app import jobs
    from app.config import Settings
    from app.models import CaseRecord

    url, _endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "deterministic")
    engine, factory = database(url)
    with factory.begin() as session:
        purchase_run = session.get(AgentRun, run_id)
        product = session.scalar(select(Product))
        case = CaseRecord(product_id=product.id)
        session.add(case)
        session.flush()
        other = CollaborationRun(case_id=case.id, revision=1, idempotency_key="other",
                                 payload={"mode": "replay"})
        jobs.enqueue(other, Settings())
        session.add(other)
        session.flush()
        other_id = other.id
        assert purchase_run.status == "queued"
    started, release = asyncio.Event(), asyncio.Event()
    effects = []
    @jobs.durable(AgentRun)
    async def first(factory, identifier, settings):
        effects.append("first")
        started.set()
        await release.wait()
        with factory.begin() as session:
            session.get(AgentRun, identifier).status = "completed"
    @jobs.durable(CollaborationRun)
    async def second(factory, identifier, settings):
        effects.append("second")
        with factory.begin() as session:
            session.get(CollaborationRun, identifier).status = "ready_for_review"
    pending = asyncio.create_task(first(factory, run_id, Settings()))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        await second(factory, other_id, Settings())
        assert effects == ["first"]
        with factory() as session:
            assert session.get(CollaborationRun, other_id).payload["job"]["attempts"] == 0
    finally:
        release.set()
        await pending
    await second(factory, other_id, Settings())
    assert effects == ["first", "second"]
    engine.dispose()


@pytest.mark.asyncio
async def test_cancelled_real_coordinator_closes_pending_case_and_task(tmp_path, monkeypatch):
    from sqlalchemy import select

    from app.config import Settings
    from app.diwali.coordinator import execute
    from app.diwali.core import LocalTransport
    from app.diwali.persistence import CaseRow, TaskRow, setup_schema

    url, _endpoint, run_id = admit_without_dispatch(tmp_path, monkeypatch, "local")
    engine, factory = database(url)
    setup_schema(engine)
    started = asyncio.Event()
    class Waiting(LocalTransport):
        async def exchange(self, message, context):
            started.set()
            await asyncio.Event().wait()
    pending = asyncio.create_task(execute(factory, run_id, Settings(), Waiting()))
    await asyncio.wait_for(started.wait(), timeout=2)
    pending.cancel()
    with pytest.raises(asyncio.CancelledError):
        await pending
    with factory() as session:
        assert session.get(AgentRun, run_id).status == "partial"
        assert {t.state for t in session.scalars(select(TaskRow))} == {"cancelled"}
        assert {c.phase for c in session.scalars(select(CaseRow))} == {"DONE"}
    engine.dispose()
