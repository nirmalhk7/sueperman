"""Executable acceptance: reset, run, poll and verify independently recorded counts."""

import argparse
import json
import time
import uuid

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--seed-only", action="store_true")
    args = parser.parse_args()
    with httpx.Client(base_url=args.api, timeout=10) as c:
        seed = c.post("/api/demo/reset")
        seed.raise_for_status()
        if args.seed_only:
            print(json.dumps(seed.json(), indent=2))
            return
        response = c.post(
            "/api/runs",
            json={
                "purchase_ids": seed.json()["purchase_ids"],
                "mode": "demo",
                "idempotency_key": str(uuid.uuid4()),
            },
        )
        response.raise_for_status()
        identifier = response.json()["run_id"]
        for _ in range(100):
            result = c.get(f"/api/runs/{identifier}")
            result.raise_for_status()
            body = result.json()
            if body["status"] in {"completed", "partial", "failed"}:
                break
            time.sleep(0.1)
        assert body["status"] == "completed", body
        expected = {
            "products_scanned": 5,
            "verified_matches": 1,
            "rejected": 1,
            "needs_review": 1,
            "simulated_settlements": 1,
            "prepared_packets": 1,
        }
        for key, value in expected.items():
            assert body["summary"][key] == value, (key, body)
        print(json.dumps(body, indent=2))


if __name__ == "__main__":
    main()
