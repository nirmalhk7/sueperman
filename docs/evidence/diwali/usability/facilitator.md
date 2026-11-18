# Facilitator setup for issue #2

Use [the current protocol](protocol-current.md) and [observation sheet](session-records-current.csv). The technical setup below was checked on `8c073aa517a886584aa0e0976ecaeef10e50926e`. The setup check is separate from participant sessions.

Give one participant one arm at a time. P01 and P03 start with D. P02 and P04 start with A. Run the command once per arm. Use a fresh private browser window for that arm and close it afterward. The two arms receive the same [synthetic CSV](purchases-current.csv). Keep the task scoring key out of the participant’s view.

From the repository root, with the locked Python and browser dependencies installed:

```sh
STUDY_ARM=D services/api/.venv/bin/python - <<'PY'
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

root = Path.cwd()
revision = "8c073aa517a886584aa0e0976ecaeef10e50926e"
arm = os.environ["STUDY_ARM"]
if arm not in {"D", "A"}:
    raise SystemExit("Use STUDY_ARM=D or STUDY_ARM=A")

with TemporaryDirectory(prefix="sueperman-study-") as name:
    archive = Path(name)
    snapshot = archive / "source.tar"
    subprocess.run(["git", "archive", "--output", str(snapshot), revision], check=True)
    subprocess.run(["tar", "-xf", str(snapshot), "-C", name], check=True)
    for item in ("services/api/.venv", "apps/web/node_modules"):
        (archive / item).symlink_to(root / item, target_is_directory=True)
    spec = importlib.util.spec_from_file_location(
        "study_verifier", archive / "scripts/verify_diwali.py"
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    inputs = (
        "docs/evidence/diwali/usability/purchases-current.csv",
        "services/api/tests/diwali/test_ui.py",
        "services/api/tests/browser_server.py",
        "services/api/tests/fixtures/cpsc-live.json",
    )
    with verifier.app_servers(archive, archive / "study") as env:
        with urlopen(env["API_URL"] + "/api/products", timeout=5) as response:
            if json.load(response) != []:
                raise RuntimeError("Study arm must begin with an empty purchase list")
        print(json.dumps({
            "arm": arm,
            "revision": revision,
            "web_url": env["WEB_URL"],
            "api_url": env["API_URL"],
            "configuration": "controlled-offline",
            "products_at_start": 0,
            "input_sha256": {
                item: hashlib.sha256((archive / item).read_bytes()).hexdigest()
                for item in inputs
            },
        }, indent=2), flush=True)
        print("Copy the setup record. Press Enter after this arm ends to stop its servers.", flush=True)
        with open("/dev/tty", encoding="utf-8") as terminal:
            terminal.readline()
PY
```

Replace `STUDY_ARM=D` with `STUDY_ARM=A` for the other arm. Wait for the JSON output before starting the timer. Copy it beside the participant code and use its loopback web URL in the browser. Enter ends the arm and removes its temporary database. If startup fails, record the error as a setup failure and restart the arm with a fresh environment.

For D, have the participant use **Check my purchases** and inspect the three distinct outcomes. For A, return to **My purchases** between the three **Investigate with agent team** cases. Keep the missing-model answer blank. Use the original PB22 case for the approval and export task. The application may display a live-path label during these exercises. The facilitator briefing explains that the isolated environment uses controlled public-source and provider responses.

Save only anonymous observations. No participant recordings, receipts, account credentials, or session artifacts with identifying information belong in the repository. At the end, report missing rows explicitly and compare each participant’s two arms before aggregating results.

The [setup preflight](setup-8c073aa.jsonl) started both arms with zero purchases and confirmed both APIs stopped afterward. The exact D command also printed the setup record in an interactive terminal and exited successfully on Enter. The [browser run](../../release-9d00e97/e2e-stdout.log) covers the deterministic and agent-team controls on this revision. These checks record software behavior. The observation sheet remains empty.
