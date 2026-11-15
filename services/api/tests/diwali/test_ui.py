"""Real browser checks use copied frontend source and task-owned disposable servers."""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest

ROOT = Path(__file__).resolve().parents[4]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def browser_env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("diwali-browser")
    web = folder / "web"
    web.mkdir()
    source = ROOT / "apps/web"
    for directory in ("app", "components", "lib", "public", "tests"):
        if (source / directory).exists():
            shutil.copytree(source / directory, web / directory)
    for path in source.iterdir():
        if path.is_file() and path.name.endswith((".ts", ".mjs", ".json")) and not path.name.endswith("tsbuildinfo"):
            shutil.copy2(path, web / path.name)
    (web / "node_modules").symlink_to(source / "node_modules", target_is_directory=True)
    api_port, web_port = free_port(), free_port()
    env = os.environ | {"DATABASE_URL": f"sqlite:///{folder}/browser.db", "DIWALI_ENABLED": "true",
        "SENTRY_DSN": "", "SENTRY_AUTH_TOKEN": "", "NEXT_PUBLIC_SENTRY_DSN": "",
        "PYTHONPATH": str(ROOT / "services/api"), "API_URL": f"http://127.0.0.1:{api_port}",
        "NEXT_PUBLIC_API_BASE_URL": f"http://127.0.0.1:{api_port}",
        "WEB_URL": f"http://127.0.0.1:{web_port}", "FRONTEND_ORIGIN": f"http://127.0.0.1:{web_port}"}
    for key in ("OPENAI_ENABLED", "OPENAI_RECEIPT_ENABLED", "GEMINI_ENABLED", "BRIGHTDATA_ENABLED",
                "CPSC_LIVE_ENABLED", "SYSTEM_ONE_ENABLED", "SETTLEMENT_LIVE_ENABLED", "BAND_ENABLED",
                "LYZR_ENABLED", "AGENT37_ENABLED", "DIWALI_LIVE_AUTHORIZED"):
        env[key] = "false"
    logs = ROOT / "docs/evidence/diwali/v2.1/browser"
    logs.mkdir(parents=True, exist_ok=True)
    env["DIWALI_EVIDENCE_DIR"] = str(logs)
    processes = []
    streams = []
    try:
        build = subprocess.run(["node", str(source / "node_modules/next/dist/bin/next"), "build", "--webpack"],
            cwd=web, env=env, capture_output=True, text=True, timeout=180, check=False)
        (logs / "build.log").write_text(build.stdout + build.stderr)
        assert build.returncode == 0, build.stdout + build.stderr
        for name, command, cwd, url in [
            ("api", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
             folder, env["API_URL"] + "/api/health"),
            ("web", ["node", str(source / "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", str(web_port)],
             web, env["WEB_URL"]),
        ]:
            stream = (logs / f"{name}.log").open("w")
            streams.append(stream)
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=stream, start_new_session=True)
            processes.append(process)
            deadline = time.monotonic() + 60
            while True:
                try:
                    with urlopen(url, timeout=2) as response:
                        if response.status == 200:
                            break
                except (URLError, TimeoutError):
                    if process.poll() is not None or time.monotonic() >= deadline:
                        pytest.fail(f"Task-owned {name} server unavailable; inspect {logs / (name + '.log')}")
                    time.sleep(0.2)
        yield web, env, logs
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        for stream in streams:
            stream.close()


def check_browser(browser_env, name):
    web, env, logs = browser_env
    command = ["node", str(ROOT / "apps/web/node_modules/@playwright/test/cli.js"), "test", "diwali.e2e.ts", "--grep", name]
    result = subprocess.run(command, cwd=web, env=env, capture_output=True, text=True, timeout=120, check=False)
    (logs / (name.replace(" ", "-") + ".log")).write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout


def test_browser_error_empty_states(browser_env):
    check_browser(browser_env, "Diwali error and empty states")


def test_browser_packet_workflow(browser_env):
    check_browser(browser_env, "Diwali packet workflow")
