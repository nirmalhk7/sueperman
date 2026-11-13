"""Catch lost persistence, duplicate runs, unsafe approvals and unsupported positives."""

import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path):
    try:
        from app.main import create_app
    except ImportError:
        pytest.fail("Persistent API workflow is not implemented")
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/test.db")) as c:
        yield c


def seed_run(c, key="test"):
    seed = c.post("/api/demo/reset")
    assert seed.status_code == 200
    ids = seed.json()["purchase_ids"]
    response = c.post("/api/runs", json={"purchase_ids": ids, "mode": "demo", "idempotency_key": key})
    assert response.status_code == 200
    return ids, response.json()["run_id"]


def test_replay_twice_has_exact_facts_and_local_only_export(client):
    for i in range(2):
        ids, run_id = seed_run(client, f"repeat-{i}")
        run = client.get(f"/api/runs/{run_id}").json()
        assert run["status"] == "completed"
        assert run["summary"] == {
            "products_scanned": 5,
            "candidates": 4,
            "verified_matches": 1,
            "rejected": 1,
            "needs_review": 1,
            "simulated_settlements": 1,
            "prepared_packets": 1,
        }
        same = client.post(
            "/api/runs", json={"purchase_ids": ids, "mode": "demo", "idempotency_key": f"repeat-{i}"}
        ).json()
        assert same["run_id"] == run_id
        opportunities = client.get("/api/opportunities", params={"run_id": run_id}).json()
        assert len(opportunities) == 4
        recalls = [o for o in opportunities if o["kind"] == "recall"]
        assert sorted(o["status"] for o in recalls) == ["needs_review", "rejected", "verified_match"]
        for o in recalls:
            detail = client.get(f"/api/opportunities/{o['id']}").json()
            assert detail["evidence"][0]["url"].startswith("https://www.cpsc.gov/Recalls/")
            assert detail["evidence"][0]["fetched_at"]
            assert detail["evidence"][0]["content_sha256"]
            assert detail["assessment"]["hard_conditions"]
        good = next(o for o in recalls if o["status"] == "verified_match")
        bad = next(o for o in recalls if o["status"] == "rejected")
        assert client.post(f"/api/opportunities/{bad['id']}/claim-packet").status_code == 409
        packet = client.post(f"/api/opportunities/{good['id']}/claim-packet").json()
        assert packet["status"] == "ready_for_review"
        assert packet["missing_documents"]
        assert "I confirm" not in packet["markdown"]
        assert "I disposed" not in packet["markdown"]
        assert client.post(f"/api/claim-packets/{packet['id']}/export").status_code == 409
        assert (
            client.post(
                f"/api/claim-packets/{packet['id']}/approve-local", json={"confirmed": False}
            ).status_code
            == 422
        )
        approved = client.post(f"/api/claim-packets/{packet['id']}/approve-local", json={"confirmed": True})
        assert approved.json()["status"] == "approved_local"
        exported = client.post(f"/api/claim-packets/{packet['id']}/export")
        assert exported.status_code == 200
        assert "text/markdown" in exported.headers["content-type"]
        assert "ZHX-PB22" in exported.text
        assert "not an external submission" in exported.text
        assert "cpsc.gov/Recalls" in exported.text
        events = client.get(f"/api/runs/{run_id}/events").json()
        assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
        assert events[-1]["stage"] == "COMPLETED"
        assert all("DEMO-001" not in json.dumps(e) for e in events)
        assert client.post(f"/api/opportunities/{good['id']}/recheck").json()["status"] == "verified_match"
        assert len(client.get("/api/opportunities", params={"run_id": run_id}).json()) == 4


def test_upload_idempotency_errors_and_health(client):
    raw = b"order_id,purchased_at,merchant,product_name,brand,model_number\nprivate-order,2024-06-12,Amazon,Power Bank,NEWDERY,ZHX-PB22\n"
    a = client.post("/api/uploads/purchases", files={"file": ("orders.csv", raw, "text/csv")})
    assert a.status_code == 200
    b = client.post("/api/uploads/purchases", files={"file": ("orders.csv", raw, "text/csv")})
    assert b.json()["product_ids"] == a.json()["product_ids"]
    products = client.get("/api/products").json()
    assert len(products) == 1
    assert "private-order" not in json.dumps(products)
    assert (
        client.post(
            "/api/uploads/purchases", files={"file": ("evil.html", b"<script/>", "text/html")}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/uploads/purchases", files={"file": ("a.csv", b'product_name\n""\n', "text/csv")}
        ).status_code
        == 422
    )
    assert client.get("/api/runs/no-such-id").status_code == 404
    assert client.get("/api/opportunities/no-such-id").status_code == 404
    assert client.post("/api/runs", json={"purchase_ids": [], "idempotency_key": "x"}).status_code == 422
    assert (
        client.post("/api/runs", json={"purchase_ids": ["missing"], "idempotency_key": "x"}).status_code
        == 404
    )
    health = client.get("/api/health").json()
    assert health["db"] == "ok"
    assert health["demo_ready"] is True
    assert "api_key" not in json.dumps(health).lower()


def test_database_survives_new_app_instance(tmp_path):
    try:
        from app.main import create_app
    except ImportError:
        pytest.fail("Persistent API workflow is not implemented")
    url = f"sqlite:///{tmp_path}/persistent.db"
    with TestClient(create_app(database_url=url)) as c:
        _, run_id = seed_run(c)
    with TestClient(create_app(database_url=url)) as c:
        assert c.get(f"/api/runs/{run_id}").json()["summary"]["verified_matches"] == 1
        assert len(c.get("/api/products").json()) == 5


def test_live_flag_invokes_cpsc_and_exposes_modes(tmp_path, monkeypatch):
    from pathlib import Path

    import respx

    from app.main import create_app

    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")
    raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    with respx.mock as router:
        route = router.get(
            "https://www.saferproducts.gov/RestWebServices/Recall",
            params={"ProductName": "NEWDERY", "format": "json"},
        ).respond(200, json=raw)
        router.get(
            "https://www.saferproducts.gov/RestWebServices/Recall",
            params={"ProductName": "DemoCo", "format": "json"},
        ).respond(200, json=[])
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/live.db")) as c:
            seed = c.post("/api/demo/reset").json()
            r = c.post(
                "/api/runs",
                json={"purchase_ids": seed["purchase_ids"], "mode": "live", "idempotency_key": "live"},
            ).json()
            run = c.get(f"/api/runs/{r['run_id']}").json()
            assert run["status"] == "completed"
            assert run["provider_modes"]["recall"] == "cpsc"
            assert run["summary"]["verified_matches"] == 1
            assert route.call_count == 1
            all_o = c.get("/api/opportunities", params={"run_id": r["run_id"]}).json()
            assert all(o["mode"] == "live" for o in all_o if o["kind"] == "recall")
            assert any(e["provider"] == "cpsc" for e in c.get(f"/api/runs/{r['run_id']}/events").json())


def test_live_failure_is_labeled_partial_not_silent_success(tmp_path, monkeypatch):
    import httpx
    import respx

    from app.main import create_app

    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")
    with respx.mock as router:
        router.get("https://www.saferproducts.gov/RestWebServices/Recall").mock(
            side_effect=httpx.ConnectError("no network")
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/fallback.db")) as c:
            seed = c.post("/api/demo/reset").json()
            r = c.post(
                "/api/runs",
                json={"purchase_ids": seed["purchase_ids"], "mode": "live", "idempotency_key": "fallback"},
            ).json()
            run = c.get(f"/api/runs/{r['run_id']}").json()
            assert run["status"] == "partial"
            assert "LIVE PROVIDER UNAVAILABLE — DEMO DATA" in run["warnings"]
            assert run["provider_modes"]["recall"] == "replay_fallback"


def test_enabled_brightdata_failure_is_partial_and_recall_facts_survive(tmp_path, monkeypatch):
    from app.main import create_app
    from app.providers.errors import ProviderUnavailable

    monkeypatch.setenv("BRIGHTDATA_ENABLED", "true")
    monkeypatch.setenv("BRIGHTDATA_API_TOKEN", "test-token")

    async def fail(self, recall):
        raise ProviderUnavailable("Bright Data unavailable")

    monkeypatch.setattr("app.providers.brightdata.BrightDataResearcher.research", fail)
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/brightdata.db")) as c:
        seed = c.post("/api/demo/reset").json()
        response = c.post(
            "/api/runs",
            json={"purchase_ids": seed["purchase_ids"], "mode": "live", "idempotency_key": "research"},
        ).json()
        r = c.get(f"/api/runs/{response['run_id']}").json()
        assert r["status"] == "partial"
        assert r["provider_modes"]["research"] == "cpsc_only_fallback"
        assert r["summary"]["verified_matches"] == 1
        assert any("Bright Data unavailable" in w for w in r["warnings"])


def test_changed_live_evidence_invalidates_previous_packet(tmp_path, monkeypatch):
    from pathlib import Path

    import respx

    from app.main import create_app

    monkeypatch.setenv("CPSC_LIVE_ENABLED", "true")
    raw = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())
    with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/changed.db")) as c:
        ids, run = seed_run(c)
        exact = next(
            o
            for o in c.get("/api/opportunities", params={"run_id": run}).json()
            if o["status"] == "verified_match"
        )
        packet = c.post(f"/api/opportunities/{exact['id']}/claim-packet").json()
        raw[0]["Description"] += " Serial restriction requires manual review."
        with respx.mock as r:
            r.get(
                "https://www.saferproducts.gov/RestWebServices/Recall",
                params={"ProductName": "NEWDERY", "format": "json"},
            ).respond(200, json=raw)
            r.get(
                "https://www.saferproducts.gov/RestWebServices/Recall",
                params={"ProductName": "DemoCo", "format": "json"},
            ).respond(200, json=[])
            c.post("/api/runs", json={"purchase_ids": ids, "mode": "live", "idempotency_key": "changed"})
        assert (
            c.post(f"/api/claim-packets/{packet['id']}/approve-local", json={"confirmed": True}).status_code
            == 409
        )
        assert c.post(f"/api/claim-packets/{packet['id']}/export").status_code == 409
        detail = c.get(f"/api/opportunities/{exact['id']}").json()
        assert detail["status"] == "needs_review"
        assert any(
            x["name"] == "unsupported_source_conditions" for x in detail["assessment"]["hard_conditions"]
        )


def test_gemini_upload_is_flagged_unconfirmed_and_cannot_match(tmp_path, monkeypatch):
    import base64

    import respx

    from app.main import create_app

    monkeypatch.setenv("GEMINI_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-token")
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1l8AAAAASUVORK5CYII="
    )
    model_output = json.dumps(
        {
            "merchant": "Demo Store",
            "purchased_at": "2024-06-12",
            "items": [{"product_name": "Power Bank", "brand": "NEWDERY", "model_number": "ZHX-PB22"}],
        }
    )
    with respx.mock as r:
        r.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
        ).respond(
            200,
            json={
                "candidates": [
                    {"content": {"role": "model", "parts": [{"text": model_output}]}, "finishReason": "STOP"}
                ]
            },
        )
        with TestClient(create_app(database_url=f"sqlite:///{tmp_path}/gemini.db")) as c:
            response = c.post("/api/uploads/purchases", files={"file": ("receipt.png", png, "image/png")})
            assert response.status_code == 200
            assert response.json()["parse_warnings"]
            p = c.get("/api/products").json()[0]
            assert p["product"]["model_number"] is None
            assert p["product"]["suggested_identifiers"]["model_number"] == "ZHX-PB22"
            run = c.post(
                "/api/runs",
                json={
                    "purchase_ids": response.json()["purchase_ids"],
                    "mode": "demo",
                    "idempotency_key": "image",
                },
            ).json()
            result = c.get(f"/api/runs/{run['run_id']}").json()
            assert result["summary"]["verified_matches"] == 0
            assert result["summary"]["needs_review"] == 1


def test_mutating_cross_origin_requests_are_rejected(client):
    response = client.post("/api/demo/reset", headers={"Origin": "https://unrelated.example"})
    assert response.status_code == 403
    assert client.get("/api/products").json() == []


def test_opportunity_list_exposes_purchase_identifier_comparison(client):
    _, run_id = seed_run(client)
    opportunities = client.get("/api/opportunities", params={"run_id": run_id}).json()
    excluded = next(o for o in opportunities if o["status"] == "rejected")
    assert excluded.get("purchase_model") == "ZHX-PB23"
    assert excluded["recall"]["models"] == ["ZHX-PB22"]
