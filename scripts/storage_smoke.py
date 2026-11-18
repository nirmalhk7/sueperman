"""Disposable persistent-Compose recovery acceptance. No live providers or user volumes."""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
PROJECT = f"sueperman-storage-check-{os.getpid()}"
ENV = os.environ | {"CONTAINER_WEB_PORT": os.environ.get("STORAGE_WEB_PORT", "3081")}
ORIGIN = f"http://127.0.0.1:{ENV['CONTAINER_WEB_PORT']}"
COMMAND = ["docker", "compose", "-f", str(ROOT / "compose.production.yaml"),
           "-f", str(ROOT / "compose.durable.yaml"), "-p", PROJECT]
FINGERPRINT = '''
import hashlib,json,sqlite3,sys
with sqlite3.connect(sys.argv[1]) as db:
    names=[row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    data={name:sorted(db.execute('SELECT * FROM "'+name.replace('"','""')+'"').fetchall(),key=repr) for name in names}
print(hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest())
'''


def compose(*args, capture=False):
    return subprocess.run([*COMMAND, *args], cwd=ROOT, env=ENV, check=True,
                          capture_output=capture, text=True, timeout=600)


def ready(client):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            response = client.get("/api/health")
            if response.status_code == 200 and client.get("/").status_code == 200:
                assert all(not item["enabled"] for item in response.json()["providers"] if item["name"] != "csv")
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise AssertionError("Task-owned durable Compose stack did not become healthy")


def fingerprint(database, running=True):
    prefix = ("exec", "-T", "api") if running else ("run", "--rm", "--no-deps", "backup")
    return compose(*prefix, "python", "-c", FINGERPRINT, database, capture=True).stdout.strip()


def main():
    try:
        compose("up", "--build", "--detach")
        with httpx.Client(base_url=ORIGIN, headers={"Origin": ORIGIN}, timeout=10) as client:
            ready(client)
            # Retain one synthetic non-demo purchase alongside the golden fixture.
            raw = b"order_id,purchased_at,merchant,product_name,brand,model_number\nSTORAGE-SYNTHETIC,2026-01-01,Test Store,Bottle,DemoCo,DC-BOTTLE-1\n"
            client.post("/api/uploads/purchases", files={"file": ("synthetic.csv", raw, "text/csv")}).raise_for_status()
            seed = client.post("/api/demo/reset").raise_for_status().json()
            run = client.post("/api/runs", json={"mode": "demo", "purchase_ids": seed["purchase_ids"],
                "idempotency_key": "storage-persistent"}).raise_for_status().json()
            deadline = time.monotonic() + 20
            while client.get(f"/api/runs/{run['run_id']}").json()["status"] != "completed":
                assert time.monotonic() < deadline
                time.sleep(0.1)
            exact = next(o for o in client.get("/api/opportunities", params={"run_id": run["run_id"]}).json()
                         if o["status"] == "verified_match")
            packet = client.post(f"/api/opportunities/{exact['id']}/claim-packet").raise_for_status().json()
            endpoint = f"/api/claim-packets/{packet['id']}"
            client.post(endpoint + "/approve-local", json={"confirmed": True}).raise_for_status()
            exported = client.post(endpoint + "/export").raise_for_status().text
            assert len(client.get("/api/products").json()) == 6
            populate = '''
import os,sys
from datetime import UTC,datetime
from sqlalchemy import select
from app.db import database
from app.models import Opportunity,ReceiptOCRUsage
from app.p1 import monitoring
engine,factory=database(os.environ['DATABASE_URL'])
monitoring.setup_schema(engine)
with factory.begin() as session:
    opportunity=session.scalar(select(Opportunity).where(Opportunity.id==sys.argv[1]))
    monitoring.set_watch(session,opportunity.id,enabled=True,observed_at=datetime.now(UTC))
    session.add(ReceiptOCRUsage(day='2026-11-17',calls=7))
engine.dispose()
'''
            compose("exec", "-T", "api", "python", "-c", populate, exact["id"])
            expected = fingerprint("/data/sueperman.db")
            result = compose("exec", "-T", "backup", "python", "-m", "app.storage", "backup",
                "--database", "/data/sueperman.db", "--directory", "/backups", capture=True)
            snapshot = json.loads(result.stdout)["snapshot"]
            assert fingerprint(snapshot + "/database.sqlite3", running=False) == expected
            compose("exec", "-T", "backup", "python", "-c",
                "import os,stat; assert os.geteuid()!=0; assert stat.S_IMODE(os.stat('/backups').st_mode)==0o700; "
                "assert not os.path.exists('/srv/app/.env')")
            compose("up", "--detach", "--force-recreate")
            ready(client)
            assert fingerprint("/data/sueperman.db") == expected
            assert client.post(endpoint + "/export").raise_for_status().text == exported
            compose("stop", "api", "backup")
            compose("run", "--rm", "--no-deps", "backup", "python", "-m", "app.storage", "restore",
                "--snapshot", snapshot, "--database", "/data/restored.db")
            assert fingerprint("/data/restored.db", running=False) == expected
            assert fingerprint("/data/sueperman.db", running=False) == expected
            ENV["SUEPERMAN_DATABASE_FILE"] = "restored.db"
            compose("up", "--detach")
            ready(client)
            assert len(client.get("/api/products").json()) == 6
            assert client.post(endpoint + "/export").raise_for_status().text == exported
            browser = subprocess.run(["pnpm", "--dir", "apps/web", "exec", "playwright", "test",
                "tests/storage.e2e.ts", "--output", "../../output/playwright/storage-" + PROJECT],
                cwd=ROOT, env=os.environ | {"WEB_URL": ORIGIN, "API_URL": ORIGIN, "STORAGE_RESTORE_PACKET_ID": packet["id"],
                    "STORAGE_EXPORT_SHA256": hashlib.sha256(exported.encode()).hexdigest()},
                capture_output=True, text=True, timeout=120, check=False)
            print(browser.stdout, end="")
            print(browser.stderr, end="")
            assert browser.returncode == 0 and "1 passed" in browser.stdout
            print("PASS: persistent Compose recreation, WAL backup, exact all-row restore, original unchanged, "
                  "approval/export via API and quota/watch/job state, non-root private snapshots, "
                  "restored imported purchases visible and historical demo drafts hidden in the browser.")
    finally:
        # Only this script's disposable project/volumes are removed.
        subprocess.run([*COMMAND, "down", "--volumes", "--remove-orphans"], cwd=ROOT, env=ENV,
                       capture_output=True, text=True, timeout=60, check=False)


if __name__ == "__main__":
    main()
