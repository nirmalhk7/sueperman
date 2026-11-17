"""Paired offline measurement. Invoke with the pytest command in results.md."""
import json
from time import perf_counter_ns

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("block,mode", [(1, "deterministic"), (1, "local"), (2, "local"), (2, "deterministic")])
def test_record_arm(block, mode, tmp_path, monkeypatch):
    monkeypatch.setenv("DIWALI_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite://")
    from app.config import ROOT
    from app.main import create_app

    oracle = json.loads((ROOT / "harness/diwali/expected.json").read_text())
    with TestClient(create_app(f"sqlite:///{tmp_path}/pilot.db")) as client:
        seed = client.post("/api/demo/reset").raise_for_status().json()
        body = dict(mode="demo", collaboration_mode=mode, purchase_ids=seed["purchase_ids"],
                    idempotency_key="pilot")
        start = perf_counter_ns()
        run_id = client.post("/api/runs", json=body).raise_for_status().json()["run_id"]
        run = client.get(f"/api/runs/{run_id}").raise_for_status().json()
        elapsed_ms = (perf_counter_ns() - start) / 1e6
        assert run["status"] == "completed"
        assert run["summary"]["products_scanned"] == len(oracle["cases"])
        items = client.get("/api/opportunities", params={"run_id": run_id}).raise_for_status().json()
        outcomes = {}
        for item in items:
            model = item["purchase_model"]
            assert model not in outcomes
            outcomes[model] = "simulated_settlement" if item["simulated"] else item["status"]
            if item["kind"] == "recall":
                detail = client.get(f"/api/opportunities/{item['id']}").raise_for_status().json()
                assert detail["evidence"][0]["url"] == oracle["source_url"]
                assert detail["evidence"][0]["quoted_excerpt"]
                assert item["mode"] == "replay"
            packet = client.post(f"/api/opportunities/{item['id']}/claim-packet")
            if item["status"] != "verified_match":
                assert packet.status_code == 409
                continue
            path = "/api/claim-packets/" + packet.raise_for_status().json()["id"]
            assert client.post(path + "/export").status_code == 409
            client.post(path + "/approve-local", json={"confirmed": True}).raise_for_status()
            draft = client.post(path + "/export").raise_for_status().text
            assert all(value in draft for value in ("ZHX-PB22", oracle["source_url"], "not an external submission"))
        observed = [outcomes.get(case["purchase_model"], "no_match") for case in oracle["cases"]]
        errors = sum(value != case["outcome"] for value, case in zip(observed, oracle["cases"]))
        messages = client.get(f"/api/runs/{run_id}/agent-messages").raise_for_status().json()["items"]
        print(json.dumps(dict(block=block, mode=mode, ms=round(elapsed_ms, 2), outcomes=observed,
                              errors=errors, messages=len(messages))))
        assert errors == 0
