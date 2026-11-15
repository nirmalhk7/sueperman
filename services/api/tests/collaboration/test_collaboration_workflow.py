"""Catch false positives, lost handoffs, unsafe answers and fake live execution."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def client(tmp_path):
    from app.db import database
    from app.main import create_app

    url = f"sqlite:///{tmp_path}/team.db"
    engine, factory = database(url)
    with TestClient(create_app(database_url=url)) as c:
        c.ledger_factory = factory
        yield c
    engine.dispose()


def start(c, index=0, key="team", mode="replay"):
    seed = c.post("/api/demo/reset").json()
    products = c.get("/api/products").json()
    product = next(p for p in products if p["id"] == seed["product_ids"][index])
    response = c.post(
        "/api/collaborations", json={"product_ids": [product["id"]], "idempotency_key": key, "mode": mode}
    )
    assert response.status_code == 200, response.text
    return response.json(), product


@pytest.mark.parametrize(
    "index,status,question",
    [(0, "ready_for_review", None), (1, "rejected", None), (3, "needs_information", "model_number")],
)
def test_offline_team_handoffs_change_board_without_sponsor_credit(client, index, status, question):
    created, _ = start(client, index)
    result = client.get(f"/api/collaborations/{created['id']}").json()
    assert result["status"] == status
    assert result["live_sponsor_proof"] == []
    assert result["mode"] == "replay"
    assert result["board"]["question_field"] == question
    assert result["board"]["finding"]
    assert result["board"]["challenge"]
    assert result["board"]["decision"]
    assert result["evidence"][0]["mode"] == "replay"
    events = client.get(f"/api/collaborations/{created['id']}/events").json()
    requests = [e for e in events if e["kind"] == "request"]
    assert [(e["sender"], e["recipient"]) for e in requests] == [
        ("controller", "scout"),
        ("scout", "skeptic"),
        ("skeptic", "builder"),
    ]
    assert len([e for e in events if e["kind"] == "result"]) == 3
    assert all(e["mode"] == "replay" for e in events)
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert "DEMO-001" not in json.dumps(events)
    if index == 1:
        assert "ZHX-PB23" in result["board"]["challenge"]
        assert "ZHX-PB22" in result["board"]["challenge"]
        assert client.post(f"/api/collaborations/{created['id']}/claim-packet").status_code == 409


def test_answers_are_explicit_revision_checked_and_do_not_modify_v1_product(client):
    created, product = start(client, 3)
    url = f"/api/collaborations/{created['id']}"
    current = client.get(url).json()
    answer = {
        "revision": current["revision"],
        "field": "model_number",
        "value": "ZHX-PB22",
        "confirmed": True,
        "idempotency_key": "answer",
    }
    assert client.post(url + "/answers", json=answer | {"confirmed": False}).status_code == 422
    assert client.post(url + "/answers", json=answer | {"field": "region"}).status_code == 409
    response = client.post(url + "/answers", json=answer)
    assert response.status_code == 200, response.text
    assert response.json()["id"] != created["id"]
    updated = client.get(f"/api/collaborations/{response.json()['id']}").json()
    assert updated["status"] == "ready_for_review"
    assert updated["revision"] == current["revision"] + 1
    assert client.post(url + "/answers", json=answer).json()["id"] == response.json()["id"]
    assert client.post(url + "/answers", json=answer | {"idempotency_key": "stale"}).status_code == 409
    original = next(p for p in client.get("/api/products").json() if p["id"] == product["id"])
    assert original["product"]["model_number"] is None


def test_replay_is_idempotent_and_draft_requires_current_local_approval(client):
    created, product = start(client)
    duplicate = client.post(
        "/api/collaborations",
        json={"product_ids": [product["id"]], "idempotency_key": "team", "mode": "replay"},
    ).json()
    assert duplicate["id"] == created["id"]
    url = f"/api/collaborations/{created['id']}"
    packet = client.post(url + "/claim-packet").json()
    assert packet["status"] == "ready_for_review"
    assert client.post(url + "/export").status_code == 409
    assert client.post(url + "/approve-local", json={"confirmed": True}).status_code == 200
    exported = client.post(url + "/export")
    assert exported.status_code == 200
    assert "OFFLINE REPLAY" in exported.text
    assert "not an external submission" in exported.text
    assert "https://www.cpsc.gov/Recalls/" in exported.text
    assert "provider_ref" not in exported.text
    assert "DEMO-001" not in exported.text
    assert client.post(url + "/claim-packet").json()["id"] == packet["id"]


def test_live_unavailable_returns_partial_without_replayed_sponsor_outcomes(client):
    created, _ = start(client, mode="live")
    result = client.get(f"/api/collaborations/{created['id']}").json()
    assert result["status"] == "partial"
    assert result["warnings"]
    assert result["live_sponsor_proof"] == []
    assert result["board"].get("decision") != "verified_match"
    assert not any(
        e["kind"] == "result" for e in client.get(f"/api/collaborations/{created['id']}/events").json()
    )


def test_public_team_rejects_private_imports_and_unconfirmed_ocr(client):
    raw = b"product_name,brand,model_number\nPower Bank,NEWDERY,ZHX-PB22\n"
    imported = client.post("/api/uploads/purchases", files={"file": ("a.csv", raw, "text/csv")}).json()
    response = client.post(
        "/api/collaborations", json={"product_ids": imported["product_ids"], "idempotency_key": "private"}
    )
    assert response.status_code == 422


def test_restart_marks_unconfirmed_tasks_partial_without_redelivery(tmp_path):
    from app.db import database
    from app.main import create_app
    from app.models import CaseRecord, CollaborationRun, Product, Purchase

    url = f"sqlite:///{tmp_path}/restart.db"
    engine, factory = database(url)
    with factory() as s:
        purchase = Purchase(import_key="restart")
        s.add(purchase)
        s.flush()
        product = Product(purchase_id=purchase.id)
        s.add(product)
        s.flush()
        case = CaseRecord(product_id=product.id, current_revision=1)
        s.add(case)
        s.flush()
        run = CollaborationRun(
            case_id=case.id,
            revision=1,
            idempotency_key="restart",
            status="challenging",
            payload={"mode": "replay", "warnings": []},
        )
        s.add(run)
        s.commit()
        run_id = run.id
    engine.dispose()
    with TestClient(create_app(database_url=url)) as c:
        result = c.get(f"/api/collaborations/{run_id}")
        assert result.status_code == 200
        assert result.json()["status"] == "partial"
        assert "restart" in result.json()["warnings"][0]
        assert len(c.get(f"/api/collaborations/{run_id}/events").json()) == 1
    engine, factory = database(url)
    with factory() as s:
        assert len(s.scalars(select(CollaborationRun)).all()) == 1
    engine.dispose()


@pytest.mark.parametrize("changed", ["evidence", "product", "rule", "skill"])
def test_changed_material_binding_revokes_approval_and_retains_history(client, monkeypatch, changed):
    from app.collaboration import roles

    created, product = start(client)
    url = f"/api/collaborations/{created['id']}"
    assert client.post(url + "/approve-local", json={"confirmed": True}).status_code == 200
    if changed == "evidence":
        original = roles.load_recall()
        monkeypatch.setattr(
            roles,
            "load_recall",
            lambda: original.model_copy(
                update={"excerpt": original.excerpt + " Updated official restriction requires review."}
            ),
        )
    elif changed == "rule":
        monkeypatch.setattr(roles, "RULE_VERSION", "26-792-v2")
    elif changed == "skill":
        monkeypatch.setattr(roles, "OFFLINE_SKILL", roles.OFFLINE_SKILL | {"version": 2})
    else:
        # Explicit confirmation is a real existing product mutation, unlike a case-only answer.
        response = client.post(
            f"/api/products/{product['id']}/confirm-identifiers",
            json={"confirmed": True, "model_number": "ZHX-PB23", "brand": "NEWDERY"},
        )
        # CSV cannot be edited through OCR API. Mutate disposable DB to simulate upstream product revision.
        assert response.status_code == 409
        from app.models import Product

        factory = client.ledger_factory
        with factory() as s:
            entity = s.get(Product, product["id"])
            entity.payload = entity.payload | {
                "product": entity.payload["product"] | {"model_number": "ZHX-PB23"}
            }
            s.commit()
    assert client.post(url + "/export").status_code == 409
    history = client.get(url + "/history").json()
    assert len(history["revisions"]) == 2
    assert history["revisions"][0]["fingerprint"] != history["revisions"][1]["fingerprint"]
    assert len(history["snapshots"]) == (2 if changed in {"evidence", "rule"} else 1)


def test_demo_reset_after_team_run_preserves_case_history_and_v1_workflow(client):
    created, _ = start(client)
    reset = client.post("/api/demo/reset")
    assert reset.status_code == 200
    assert len(reset.json()["product_ids"]) == 5
    assert client.get(f"/api/collaborations/{created['id']}/history").json()["revisions"]
    run = client.post(
        "/api/runs",
        json={
            "purchase_ids": reset.json()["purchase_ids"],
            "idempotency_key": "v1-after-team",
            "mode": "demo",
        },
    )
    assert run.status_code == 200
    assert client.get(f"/api/runs/{run.json()['run_id']}").json()["summary"]["verified_matches"] == 1


@pytest.mark.parametrize("fault", ["outage", "timeout", "malformed"])
def test_role_failure_preserves_evidence_and_never_retries_paid_work(client, monkeypatch, fault):
    from app.collaboration import roles

    attempts = []

    async def fail(product):
        attempts.append(1)
        if fault == "timeout":
            raise TimeoutError
        if fault == "malformed":
            return {"command": "arbitrary shell"}
        raise RuntimeError("Bearer sensitive-provider-secret")

    monkeypatch.setattr(roles, "scout", fail)
    created, _ = start(client)
    result = client.get(f"/api/collaborations/{created['id']}").json()
    assert result["status"] == "partial"
    assert result["evidence"]
    assert result["warnings"]
    assert "sensitive-provider-secret" not in json.dumps(result)
    assert len(attempts) == 1
    assert result["model_calls"] == 0
    assert result["task_requests"] <= 6
    assert client.post(f"/api/collaborations/{created['id']}/export").status_code == 409


def test_only_one_case_is_admitted_and_queued_work_blocks_reset(client):
    from app.models import CollaborationRun

    created, product = start(client)
    with client.ledger_factory() as s:
        run = s.get(CollaborationRun, created["id"])
        run.status = "challenging"
        s.commit()
    assert (
        client.post(
            "/api/collaborations", json={"product_ids": [product["id"]], "idempotency_key": "another"}
        ).status_code
        == 409
    )
    assert client.post("/api/demo/reset").status_code == 409
    assert (
        client.post(
            "/api/collaborations",
            json={"product_ids": [product["id"], product["id"]], "idempotency_key": "oversize"},
        ).status_code
        == 422
    )


def test_real_deadline_cancels_role_and_preserves_evidence(tmp_path, monkeypatch):
    import asyncio

    from app.main import create_app

    monkeypatch.setenv("COLLABORATION_TIMEOUT_SECONDS", "0.01")

    async def delayed(product):
        await asyncio.sleep(2)
        raise AssertionError("Deadline failed to cancel source lookup")

    monkeypatch.setattr("app.collaboration.roles.scout", delayed)
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/deadline.db")) as c:
        created, _ = start(c)
        result = c.get(f"/api/collaborations/{created['id']}").json()
        assert result["status"] == "partial"
        assert result["warnings"] == ["Team deadline exceeded; evidence preserved."]
        assert result["evidence"]
        assert result["task_requests"] == 1
        assert not any(
            e["kind"] == "result" for e in c.get(f"/api/collaborations/{created['id']}/events").json()
        )


def test_local_team_requires_ocr_identifier_confirmation(tmp_path, monkeypatch):
    from app.db import database
    from app.main import create_app
    from app.models import Product

    monkeypatch.setenv("COLLABORATION_PUBLIC_DEMO", "false")
    url = f"sqlite:///{tmp_path}/ocr.db"
    engine, factory = database(url)
    with TestClient(create_app(database_url=url)) as c:
        raw = b"product_name,brand,model_number\nPower Bank,NEWDERY,ZHX-PB22\n"
        imported = c.post("/api/uploads/purchases", files={"file": ("a.csv", raw, "text/csv")}).json()
        with factory() as s:
            product = s.get(Product, imported["product_ids"][0])
            product.payload = product.payload | {"source_type": "image"}
            s.commit()
        assert (
            c.post(
                "/api/collaborations", json={"product_ids": imported["product_ids"], "idempotency_key": "ocr"}
            ).status_code
            == 422
        )
    engine.dispose()


def test_unavailable_recorded_source_admits_a_partial_case_instead_of_server_error(client, monkeypatch):
    def unavailable():
        raise OSError("recorded source absent")

    monkeypatch.setattr("app.collaboration.roles.load_recall", unavailable)
    created, _ = start(client)
    result = client.get(f"/api/collaborations/{created['id']}").json()
    assert result["status"] == "partial"
    assert result["warnings"]
    assert result["live_sponsor_proof"] == []
    assert result["board"] == {}


def test_source_loss_after_approval_revokes_export_but_keeps_prior_snapshot(client, monkeypatch):
    created, _ = start(client)
    url = f"/api/collaborations/{created['id']}"
    assert client.post(url + "/approve-local", json={"confirmed": True}).status_code == 200

    def unavailable():
        raise OSError("recorded source absent")

    monkeypatch.setattr("app.collaboration.roles.load_recall", unavailable)
    assert client.post(url + "/export").status_code == 409
    assert client.get(url).json()["status"] == "partial"
    history = client.get(url + "/history").json()
    assert len(history["snapshots"]) == 1
    assert len(history["revisions"]) == 2
