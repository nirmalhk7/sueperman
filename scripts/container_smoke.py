"""Build isolated deployment containers and verify the same-origin offline workflow.

Never loads provider keys. Removes only this process's Compose containers/volumes.
"""

import os
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROJECT = f"sueperman-check-{os.getpid()}"
COMMAND = [
    "docker",
    "compose",
    "-f",
    str(ROOT / "compose.production.yaml"),
    "-p",
    PROJECT,
]
ORIGIN = f"http://127.0.0.1:{os.environ.get('CONTAINER_WEB_PORT', '3080')}"


def compose(*args, **kwargs):
    return subprocess.run(
        [*COMMAND, *args], cwd=ROOT, check=True, timeout=1200, **kwargs
    )


def wait_for(client, path):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        try:
            response = client.get(path)
            if response.status_code == 200:
                return response
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise AssertionError(f"Container endpoint did not become healthy: {path}")


def main():
    try:
        compose("up", "--build", "--detach")
        with httpx.Client(
            base_url=ORIGIN, headers={"Origin": ORIGIN}, timeout=5
        ) as client:
            health = wait_for(client, "/api/health").json()
            assert health["db"] == "ok"
            assert all(
                not p["enabled"] for p in health["providers"] if p["name"] != "csv"
            )
            home = wait_for(client, "/").text
            assert "Sueperman" in home
            assert "SHARED WORKSPACE" in home and "Upload purchases or receipt" in home
            assert "Uploaded purchase details are visible to other visitors." in home
            seeded = client.post("/api/demo/reset")
            seeded.raise_for_status()
            started = client.post(
                "/api/runs",
                json={
                    "purchase_ids": seeded.json()["purchase_ids"],
                    "mode": "demo",
                    "idempotency_key": "container-acceptance",
                },
            )
            started.raise_for_status()
            run_id = started.json()["run_id"]
            for _ in range(40):
                run = client.get(f"/api/runs/{run_id}").json()
                if run["status"] in {"completed", "partial", "failed"}:
                    break
                time.sleep(0.25)
            assert run["status"] == "completed", run["status"]
            assert run["summary"] == {
                "products_scanned": 5,
                "candidates": 4,
                "verified_matches": 1,
                "rejected": 1,
                "needs_review": 1,
                "simulated_settlements": 1,
                "prepared_packets": 1,
            }
            cases = client.get("/api/opportunities", params={"run_id": run_id}).json()
            exact = next(o for o in cases if o["status"] == "verified_match")
            excluded = next(o for o in cases if o["status"] == "rejected")
            assert (
                client.post(
                    f"/api/opportunities/{excluded['id']}/claim-packet"
                ).status_code
                == 409
            )
            packet = client.post(
                f"/api/opportunities/{exact['id']}/claim-packet"
            ).json()
            pid = packet["id"]
            assert client.post(f"/api/claim-packets/{pid}/export").status_code == 409
            approved = client.post(
                f"/api/claim-packets/{pid}/approve-local", json={"confirmed": True}
            )
            approved.raise_for_status()
            exported = client.post(f"/api/claim-packets/{pid}/export")
            exported.raise_for_status()
            assert "ZHX-PB22" in exported.text
            assert "not an external submission" in exported.text
        compose(
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import os; from pathlib import Path; assert os.geteuid()!=0; "
            "assert not Path('/srv/app/.env').exists()",
        )
        compose(
            "exec",
            "-T",
            "web",
            "node",
            "-e",
            "const fs=require('fs');if(process.getuid()===0||fs.existsSync('/srv/app/apps/web/.env.local'))process.exit(1)",
        )
        compose(
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            "import platform; assert platform.machine() == 'x86_64'",
        )
        compose("exec", "-T", "api", "npx", "--version")
        compose("exec", "-T", "api", "python", "-c",
            "import os,sys;sys.path.insert(0,'/srv/app/services/api')\n"
            "from sqlalchemy import select\nfrom app.db import database\n"
            "from app.models import Purchase\nfrom app.diwali.band_settings import validate_synthetic\n"
            "engine,factory=database(os.environ['DATABASE_URL'])\n"
            "with factory() as session:\n"
            "    identifiers=session.scalars(select(Purchase.id).where(Purchase.demo.is_(True))).all()\n"
            "    assert len(identifiers)==5\n"
            "    validate_synthetic(session,identifiers)\n")
        browser = subprocess.run(
            [
                "pnpm",
                "--dir",
                "apps/web",
                "exec",
                "playwright",
                "test",
                "tests/deletion.e2e.ts",
                "--output",
                "../../output/playwright/container-" + PROJECT,
            ],
            cwd=ROOT,
            env=os.environ | {"WEB_URL": ORIGIN, "API_URL": ORIGIN},
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        print(browser.stdout, end="")
        print(browser.stderr, end="")
        assert browser.returncode == 0 and "3 passed" in browser.stdout
        print(
            "PASS: production containers, same-origin API, exact/negative demo and local export via API, "
            "desktop/mobile deletion and confirmed re-import, shared-history consent, non-root users, no env files."
        )
    finally:
        subprocess.run(
            [*COMMAND, "down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            check=False,
            timeout=60,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


if __name__ == "__main__":
    main()
