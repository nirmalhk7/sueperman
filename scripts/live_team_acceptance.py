"""Opt-in correlated live acceptance. Default is read-only preflight, never paid calls.

With --execute, at most three synthetic team runs (six application model requests)
plus a provider-disabled check run against a new private disposable database.
Vendor-internal usage still requires provider receipts and is not claimed here.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services/api"))
from app.collaboration.live import blockers
from app.config import Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Explicitly permit bounded real sponsor calls",
    )
    parser.add_argument(
        "--max-model-requests",
        type=int,
        default=0,
        help="Must explicitly approve six application requests",
    )
    args = parser.parse_args()
    settings = Settings()
    missing = blockers(settings)
    if missing or not settings.demo_mode or not args.execute:
        print(
            json.dumps(
                {
                    "execution_performed": False,
                    "configuration_blockers": missing,
                    "synthetic_demo_enabled": settings.demo_mode,
                    "next": "Configure/review accounts; then explicitly opt in with --execute --max-model-requests 6",
                },
                indent=2,
            )
        )
        return 2 if missing or not settings.demo_mode else 0
    if args.max_model_requests != 6:
        parser.error(
            "Approve exactly six application model requests; this is not a vendor billing guarantee"
        )
    from app.main import create_app
    from fastapi.testclient import TestClient

    directory = Path(tempfile.mkdtemp(prefix="sueperman-live-proof-"))
    database = f"sqlite:///{directory / 'private-case-ledger.db'}"
    report = {
        "mode": "live",
        "live_sponsor_proof_reviewed": False,
        "cases": [],
        "vendor_internal_calls": "unverified",
    }
    try:
        with TestClient(create_app(database_url=database)) as client:
            response = client.post("/api/demo/reset")
            response.raise_for_status()
            products = response.json()["product_ids"]
            for index, expected in [
                (0, "ready_for_review"),
                (1, "rejected"),
                (3, "needs_information"),
            ]:
                response = client.post(
                    "/api/collaborations",
                    json={
                        "product_ids": [products[index]],
                        "mode": "live",
                        "idempotency_key": str(uuid4()),
                    },
                )
                response.raise_for_status()
                path = "/api/collaborations/" + response.json()["id"]
                case = client.get(path).json()
                events = client.get(path + "/events").json()
                report["cases"].append(
                    {
                        "case_id": case["id"],
                        "expected": expected,
                        "status": case["status"],
                        "elapsed_ms": case["elapsed_ms"],
                        "application_model_requests": case["model_calls"],
                        "events": events,
                        "evidence": case["board"].get("evidence", []),
                        "skill": case["skill"],
                    }
                )
                assert case["status"] == expected, (
                    "Live case incomplete; no automatic retry"
                )
                assert case["elapsed_ms"] <= settings.collaboration_run_seconds * 1000
                assert case["model_calls"] <= 2 and case["task_requests"] == 3
                assert [e["provider"] for e in events if e["kind"] == "result"] == [
                    "agent37",
                    "adal",
                    "lyzr",
                ]
                if expected == "ready_for_review":
                    client.post(
                        path + "/approve-local",
                        json={"revision": case["revision"], "confirmed": True},
                    ).raise_for_status()
                    client.post(
                        path + "/export", json={"revision": case["revision"]}
                    ).raise_for_status()
        previous = os.environ.get("BAND_ENABLED")
        os.environ["BAND_ENABLED"] = "false"
        try:
            with TestClient(create_app(database_url=database)) as client:
                response = client.post(
                    "/api/collaborations",
                    json={
                        "product_ids": [products[0]],
                        "mode": "live",
                        "idempotency_key": str(uuid4()),
                    },
                )
                response.raise_for_status()
                case = client.get("/api/collaborations/" + response.json()["id"]).json()
                assert (
                    case["status"] == "partial" and "band" in case["blocked_providers"]
                )
                assert case["model_calls"] == 0
                report["disabled_provider"] = {
                    "provider": "band",
                    "status": "partial",
                    "model_requests": 0,
                }
        finally:
            if previous is None:
                os.environ.pop("BAND_ENABLED", None)
            else:
                os.environ["BAND_ENABLED"] = previous
        report["application_acceptance_passed"] = True
    except Exception:  # noqa: BLE001 — sanitize provider failures at the CLI boundary.
        # Raw errors can include provider headers or credentials. Persist only sanitized state.
        report["application_acceptance_passed"] = False
        report["failure"] = (
            "A live run failed or exceeded its bounds; inspect the private ledger, do not auto-retry."
        )
    (directory / "sanitized-report.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "artifact_directory": str(directory),
                "application_acceptance_passed": report[
                    "application_acceptance_passed"
                ],
                "live_sponsor_proof_reviewed": False,
            }
        )
    )
    return 0 if report["application_acceptance_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
