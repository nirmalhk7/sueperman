import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.collaboration.contracts import CaseResult, EvidenceSnapshot
from app.collaboration.controller import verify_result
from app.collaboration.ledger import digest
from app.db import database
from app.main import create_app
from app.models import Collaboration, CollaborationRevision, CollaborationTask, Product
from app.schemas import Condition, MatchResult


def setup(tmp_path):
    url = f"sqlite:///{tmp_path}/isolated.db"
    app = create_app(database_url=url)
    engine, factory = database(url)
    return app, engine, factory


def run(c, index=0):
    seed = c.post("/api/demo/reset").json()
    started = c.post(
        "/api/collaborations",
        json={"product_ids": [seed["product_ids"][index]], "mode": "replay", "idempotency_key": "guard"},
    ).json()
    path = f"/api/collaborations/{started['id']}"
    return path, c.get(path).json()


@pytest.mark.parametrize("mutation", ["product", "rule", "skill", "packet", "evidence"])
def test_material_change_prevents_export_and_retains_history(tmp_path, mutation):
    app, engine, factory = setup(tmp_path)
    with TestClient(app) as c:
        path, case = run(c)
        body = {"revision": case["revision"]}
        assert c.post(path + "/approve-local", json=body | {"confirmed": True}).status_code == 200
        with factory() as s:
            row = s.scalar(select(CollaborationRevision))
            if mutation == "product":
                product = s.get(Product, case["product_id"])
                product.payload = product.payload | {
                    "product": product.payload["product"] | {"model_number": "ZHX-PB23"}
                }
            elif mutation == "packet":
                row.payload = row.payload | {"packet": row.payload["packet"] | {"markdown": "Altered packet"}}
            elif mutation == "evidence":
                row.payload = row.payload | {"evidence": []}
            else:
                row.payload = row.payload | {
                    mutation + ("_version" if mutation == "rule" else "_hash"): "changed"
                }
            s.commit()
        assert c.post(path + "/export", json=body).status_code == 409
        assert len(c.get(path).json()["history"]) == 1
    engine.dispose()


def test_fault_is_partial_without_retry_and_does_not_leak_error(tmp_path, monkeypatch):
    from app.collaboration import controller

    calls = []

    async def fail(task, match, prior):
        calls.append(task.recipient)
        raise RuntimeError("SECRET_PROVIDER_KEY")

    monkeypatch.setattr(controller, "replay_role", fail)
    app, engine, _ = setup(tmp_path)
    with TestClient(app) as c:
        path, case = run(c)
        assert case["status"] == "partial"
        assert calls == ["scout"]
        assert "SECRET_PROVIDER_KEY" not in json.dumps(case)
        assert case["history"][0]["evidence"]
        assert len(c.get(path + "/events").json()) == 1
    engine.dispose()


def test_restart_marks_unconfirmed_work_partial(tmp_path):
    app, engine, factory = setup(tmp_path)
    with TestClient(app) as c:
        path, case = run(c)
    with factory() as s:
        row = s.get(Collaboration, case["id"])
        row.status = "challenging"
        task = s.scalar(select(CollaborationTask))
        task.status = "pending"
        s.commit()
    with TestClient(create_app(database_url=str(engine.url))) as c:
        recovered = c.get(path).json()
        assert recovered["status"] == "partial"
        assert "restart" in recovered["warnings"][0]
        assert c.post(path + "/export", json={"revision": case["revision"]}).status_code == 409
    engine.dispose()


def test_private_fields_stay_out_of_roles_and_exports(tmp_path):
    app, engine, factory = setup(tmp_path)
    with TestClient(app) as c:
        path, case = run(c)
        with factory() as s:
            tasks = s.scalars(select(CollaborationTask)).all()
            data = json.dumps([r.payload for r in tasks])
            assert all(word not in data for word in ["merchant", "order_reference", "receipt", "api_key"])
        assert "merchant" not in case["packet"]["completed_fields"]
        assert "provider_reference" not in c.get(path + "/events").text
    engine.dispose()


def test_model_cannot_assert_success_or_invent_exclusions():
    base = {
        "case_id": "case",
        "task_id": "task",
        "revision": digest("revision"),
        "provider": "lyzr",
        "role": "builder",
        "mode": "live",
        "status": "completed",
        "findings": [],
        "source_refs": ["26-792"],
    }
    unknown = MatchResult(
        status="needs_review", conditions=[Condition(name="model_number", expected="ZHX-PB22")]
    )
    with pytest.raises(ValueError):
        verify_result(CaseResult(**base), unknown)
    with pytest.raises(ValidationError):
        CaseResult(**base, text="Guaranteed refund; claim submitted")
    with pytest.raises(ValueError):
        verify_result(
            CaseResult(
                **(
                    base
                    | {
                        "role": "skeptic",
                        "findings": [
                            {
                                "code": "excluded_condition",
                                "condition": "model_number",
                                "source_ref": "26-792",
                            }
                        ],
                    }
                )
            ),
            unknown,
        )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.cpsc.gov/Recalls/x",
        "https://evil.example/Recalls/x",
        "https://www.cpsc.gov.evil.example/Recalls/x",
    ],
)
def test_source_policy_rejects_untrusted_urls(url):
    with pytest.raises(ValidationError):
        EvidenceSnapshot(
            id="x",
            publisher="x",
            url=url,
            fetched_at="2026-11-15T00:00:00Z",
            content_sha256=digest("x"),
            rule_version="v1",
            excerpt="x",
            mode="replay",
        )


def test_new_primary_source_revision_blocks_previously_approved_team_packet(tmp_path):
    from app.models import Opportunity

    app, engine, factory = setup(tmp_path)
    with TestClient(app) as c:
        path, case = run(c)
        body = {"revision": case["revision"]}
        assert c.post(path + "/approve-local", json=body | {"confirmed": True}).status_code == 200
        with factory() as s:
            s.add(
                Opportunity(
                    product_id=case["product_id"],
                    kind="recall",
                    source_id="26-792",
                    official_url="https://www.cpsc.gov/Recalls/2026/changed",
                    demo=True,
                    payload={"recall": {"excerpt": "New serial restriction"}, "status": "needs_review"},
                )
            )
            s.commit()
        assert c.post(path + "/export", json=body).status_code == 409
        assert c.get(path).json()["approval"] is None
    engine.dispose()


@pytest.mark.parametrize("model", ["ZHX-PB23", "ZHX-PB22-A", "ZHX.PB22", "ZHX/PB22"])
def test_near_match_and_punctuation_variants_are_excluded(tmp_path, model):
    app, engine, factory = setup(tmp_path)
    with TestClient(app) as c:
        seed = c.post("/api/demo/reset").json()
        with factory() as s:
            product = s.get(Product, seed["product_ids"][0])
            product.model_number = model
            product.payload = product.payload | {
                "product": product.payload["product"] | {"model_number": model}
            }
            s.commit()
        case = c.post(
            "/api/collaborations",
            json={"product_ids": [seed["product_ids"][0]], "idempotency_key": "variants"},
        ).json()
        detail = c.get(f"/api/collaborations/{case['id']}").json()
        assert detail["status"] == "rejected"
        assert detail["packet"] is None
    engine.dispose()


def test_source_outage_retains_explicit_partial_and_no_packet(tmp_path, monkeypatch):
    async def unavailable(self, product):
        raise TimeoutError("source unavailable")

    monkeypatch.setattr("app.providers.cpsc.FixtureRecallSource.search", unavailable)
    app, engine, _ = setup(tmp_path)
    with TestClient(app) as c:
        _, case = run(c)
        assert case["status"] == "partial"
        assert case["packet"] is None
        assert case["warnings"]
    engine.dispose()


def test_quota_and_non_synthetic_product_are_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLABORATION_DAILY_LIMIT", "0")
    app, engine, factory = setup(tmp_path)
    with TestClient(app) as c:
        seed = c.post("/api/demo/reset").json()
        body = {"product_ids": [seed["product_ids"][0]], "idempotency_key": "quota"}
        assert c.post("/api/collaborations", json=body).status_code == 429
        with factory() as s:
            product = s.get(Product, seed["product_ids"][0])
            product.demo = False
            s.commit()
        assert c.post("/api/collaborations", json=body).status_code == 422
    engine.dispose()


@pytest.mark.asyncio
async def test_shared_deadline_stops_role_without_retry(tmp_path, monkeypatch):
    import asyncio

    from app.collaboration import controller

    monkeypatch.setenv("COLLABORATION_RUN_SECONDS", "1")
    calls = []

    async def slow(task, match, prior):
        calls.append(task.recipient)
        await asyncio.sleep(2)

    monkeypatch.setattr(controller, "replay_role", slow)
    app, engine, _ = setup(tmp_path)
    with TestClient(app) as c:
        _, case = run(c)
        assert case["status"] == "partial"
        assert calls == ["scout"]
        assert case["packet"] is None
    engine.dispose()


def test_demo_reset_does_not_reset_daily_team_budget(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLABORATION_DAILY_LIMIT", "1")
    app, engine, _ = setup(tmp_path)
    with TestClient(app) as c:
        run(c)
        seed = c.post("/api/demo/reset").json()
        response = c.post(
            "/api/collaborations",
            json={"product_ids": [seed["product_ids"][0]], "idempotency_key": "after-reset"},
        )
        assert response.status_code == 429
    engine.dispose()


@pytest.mark.parametrize("status", ["partial", "failed", "timed_out"])
def test_incomplete_role_cannot_become_ready(tmp_path, monkeypatch, status):
    from app.collaboration import controller

    original = controller.replay_role

    async def incomplete(task, match, prior):
        result = await original(task, match, prior)
        return result.model_copy(update={"status": status}) if task.recipient == "builder" else result

    monkeypatch.setattr(controller, "replay_role", incomplete)
    app, engine, _ = setup(tmp_path)
    with TestClient(app) as c:
        _, case = run(c)
        assert case["status"] == "partial"
        assert case["packet"] is None
    engine.dispose()


def test_review_cannot_silently_omit_seeded_exclusion():
    result = CaseResult(
        case_id="case",
        task_id="task",
        revision=digest("r"),
        provider="adal",
        role="skeptic",
        mode="live",
        status="completed",
        findings=[],
        source_refs=["26-792"],
    )
    match = MatchResult(
        status="rejected",
        conditions=[Condition(name="model_number", expected="ZHX-PB22", observed="ZHX-PB23", status="false")],
    )
    with pytest.raises(ValueError, match="omitted"):
        verify_result(result, match)


def test_challenge_requires_citation_on_each_condition_finding():
    result = CaseResult(
        case_id="case",
        task_id="task",
        revision=digest("r"),
        provider="adal",
        role="skeptic",
        mode="live",
        status="completed",
        findings=[{"code": "excluded_condition", "condition": "model_number"}],
        source_refs=["26-792"],
    )
    match = MatchResult(
        status="rejected",
        conditions=[Condition(name="model_number", expected="ZHX-PB22", observed="ZHX-PB23", status="false")],
    )
    with pytest.raises(ValueError, match="citation"):
        verify_result(result, match)
