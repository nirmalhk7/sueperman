"""Exercise live provider HTTP boundaries without spending account credits."""

import importlib
import json
from pathlib import Path

import httpx
import pytest

from app.collaboration.contracts import CaseTask
from app.schemas import ProductInput


def module():
    try:
        return importlib.import_module("app.collaboration.live_providers")
    except ModuleNotFoundError:
        pytest.fail("Live role provider boundaries are not implemented")


async def test_scout_runs_public_query_and_deletes_only_its_owned_instance(tmp_path):
    live = module()
    calls = []
    rows = json.loads((Path(__file__).parents[1] / "fixtures/cpsc-live.json").read_text())

    def respond(request):
        calls.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "owned-test", "deleted": True})
        if request.url.path == "/v1/instances":
            return httpx.Response(201, json={"id": "owned-test", "status": "running"})
        return httpx.Response(200, json={"exit_code": 0, "truncated": False,
            "stdout": json.dumps({"rows": rows, "worker_sha256": live.PUBLIC_WORKER_SHA256}), "stderr": ""})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        scout = live.PublicScout("secret-key", client=client)
        product = ProductInput(product_name="Portable Power Bank", brand="NEWDERY", model_number="ZHX-PB22",
                               merchant="Private merchant", order_reference_redacted="PRIVATE-ORDER")
        records, receipt = await scout.investigate(product, "run", "case")
    assert records[0].mode == "live"
    assert records[0].models == ["ZHX-PB22"]
    assert receipt["provider"] == "agent37"
    assert [r.method for r in calls] == ["POST", "POST", "DELETE"]
    assert str(calls[1].url) == "https://sandbox.agent37.app/v1/instances/owned-test/exec"
    assert calls[1].headers["X-Agent37-Key"] == "secret-key"
    body = json.loads(calls[1].content)
    assert "Private merchant" not in body["command"]
    assert "PRIVATE-ORDER" not in body["command"]
    assert "secret-key" not in body["command"]
    assert str(calls[2].url) == "https://api.agent37.com/v1/instances/owned-test"


async def test_scout_outage_cleans_up_without_retry_or_recorded_result():
    live = module()
    calls = []

    def respond(request):
        calls.append(request)
        if request.method == "DELETE":
            return httpx.Response(200, json={"id": "owned-test", "deleted": True})
        if request.url.path == "/v1/instances":
            return httpx.Response(201, json={"id": "owned-test", "status": "running"})
        return httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError):
            await live.PublicScout("secret-key", client=client).investigate(
                ProductInput(product_name="Power bank", brand="NEWDERY"), "run", "case")
    assert [r.method for r in calls] == ["POST", "POST", "DELETE"]


def task(role="skeptic"):
    return CaseTask(case_id="case", task_id="task", revision=1,
        sender="scout" if role == "skeptic" else "skeptic", recipient=role,
        kind="counterexample_review" if role == "skeptic" else "case_board_construction",
        deduplication_key="one", source_refs=["26-792"], remaining_ms=30000, mode="live")


async def test_reviewer_uses_saved_profile_and_rejects_unknown_sources():
    live = module()
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, json={"response": json.dumps({
            "review_note": "The exact model must match the supplied notice.",
            "requested_fields": [], "evidence_refs": ["invented"], "uncertainty": False})})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        reviewer = live.LyzrRoles("secret-key", "reviewer", "builder", "saved-user", client=client)
        with pytest.raises(ValueError):
            await reviewer.review(task(), {"product": {"model_number": "ZHX-PB22"}, "evidence": []})
    assert len(calls) == 1
    assert calls[0].headers["x-api-key"] == "secret-key"
    payload = json.loads(calls[0].content)
    assert payload["agent_id"] == "reviewer"
    assert payload["user_id"] == "saved-user"


async def test_builder_cannot_change_deterministic_findings():
    live = module()
    expected = {"status": "rejected", "findings": [], "missing_conditions": [], "source_refs": ["26-792"]}

    def respond(request):
        output = {"schema_version": 1, "task_id": "task", "case_id": "case", "revision": 1,
            "provider": "lyzr", "mode": "live", "status": "completed", "findings": [],
            "missing_conditions": [], "source_refs": ["26-792"], "provider_ref": None, "duration_ms": 0}
        return httpx.Response(200, json={"response": json.dumps(output)})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ValueError):
            await live.LyzrRoles("key", "reviewer", "builder", "user", client=client).build(
                task("builder"), {"validated_review": expected})


@pytest.mark.parametrize("fault", ["missing-citation", "invented-model", "duplicate-question"])
async def test_reviewer_rejects_unattributed_or_invented_advice(fault):
    live = module()
    advice = {"review_note": "Compare supplied model ZHX-PB22.", "evidence_refs": ["26-792"],
        "requested_fields": [], "uncertainty": False}
    if fault == "missing-citation":
        advice["evidence_refs"] = []
    elif fault == "invented-model":
        advice["review_note"] = "Compare model FAKE-999."
    else:
        advice["requested_fields"] = ["affected_models", "affected_models"]
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200,
        json={"response": json.dumps(advice)}))) as client:
        with pytest.raises(ValueError):
            await live.LyzrRoles("key", "reviewer", "builder", "user", client=client).review(task(), {
                "product": {"model_number": "ZHX-PB22"}, "evidence": {"models": ["ZHX-PB22"]}})
