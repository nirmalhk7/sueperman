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

SERVER = "import copy,json,os\nfrom pathlib import Path\nfrom urllib.parse import parse_qs\nimport httpx\n\nOriginalClient=httpx.AsyncClient\nroot=Path(os.environ['PYTHONPATH'].split(os.pathsep)[0]).parents[1]\nrows={key:json.loads((root/'services/api/tests/fixtures/p1-recalls'/file).read_text())\n      for key,file in [('Flaunt','26610.json'),('iStore','25390.json')]}\ndef response(request):\n    assert request.url.host=='www.saferproducts.gov', 'Unregistered external test request'\n    control=json.loads(Path(os.environ['P1_BROWSER_CONTROL']).read_text())\n    if control['mode']=='unavailable':return httpx.Response(503)\n    query=parse_qs(request.url.query.decode())['ProductName'][0]\n    selected=copy.deepcopy(rows.get(query))\n    if selected is None:return httpx.Response(200,json=[])\n    if control['mode']=='changed':selected['Description']+=' Only serial TEST100 is included.'\n    return httpx.Response(200,json=[selected])\nclass OfflineClient(OriginalClient):\n    def __init__(self,*args,**kwargs):\n        kwargs['transport']=httpx.MockTransport(response)\n        super().__init__(*args,**kwargs)\nhttpx.AsyncClient=OfflineClient\nfrom app.providers.cpsc import CPSCRecallSource\noriginal_init=CPSCRecallSource.__init__\ndef isolated_init(self,*args,**kwargs):\n    kwargs.setdefault('cache_dir',Path(os.environ['P1_BROWSER_CONTROL']).parent/'cache')\n    original_init(self,*args,**kwargs)\nCPSCRecallSource.__init__=isolated_init\nfrom app.main import app\n"


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="module")
def p1_browser_env(tmp_path_factory):
    folder = tmp_path_factory.mktemp("p1-browser")
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
    env = os.environ | {"DATABASE_URL": f"sqlite:///{folder}/browser.db", "DIWALI_ENABLED": "true", "P1_ENABLED": "true", "P1_MONITOR_ENABLED": "true",
        "P1_MONITOR_POLL_SECONDS": "1",
        "SENTRY_DSN": "", "SENTRY_AUTH_TOKEN": "", "NEXT_PUBLIC_SENTRY_DSN": "",
        "PYTHONPATH": str(ROOT / "services/api"), "API_URL": f"http://127.0.0.1:{api_port}",
        "NEXT_PUBLIC_API_BASE_URL": f"http://127.0.0.1:{api_port}",
        "WEB_URL": f"http://127.0.0.1:{web_port}", "FRONTEND_ORIGIN": f"http://127.0.0.1:{web_port}"}
    for key in ("OPENAI_ENABLED", "OPENAI_RECEIPT_ENABLED", "GEMINI_ENABLED", "BRIGHTDATA_ENABLED",
                "SYSTEM_ONE_ENABLED", "SETTLEMENT_LIVE_ENABLED", "BAND_ENABLED",
                "LYZR_ENABLED", "AGENT37_ENABLED", "DIWALI_LIVE_AUTHORIZED"):
        env[key] = "false"
    env["CPSC_LIVE_ENABLED"] = "true"
    env["P1_BROWSER_CONTROL"] = str(folder / "source-state.json")
    (folder / "source-state.json").write_text('{"mode":"unchanged"}')
    env["PYTHONPATH"] += os.pathsep + str(folder)
    (folder / "p1_test_server.py").write_text(SERVER)
    logs = ROOT / "docs/evidence/diwali/p1/browser"
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
            ("api", [sys.executable, "-m", "uvicorn", "p1_test_server:app", "--host", "127.0.0.1", "--port", str(api_port)],
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



def test_p1_browser_acceptance(p1_browser_env):
    web, env, logs = p1_browser_env
    result = subprocess.run(["node", str(ROOT / "apps/web/node_modules/@playwright/test/cli.js"),
        "test", "p1.e2e.ts"], cwd=web, env=env, capture_output=True, text=True, timeout=180, check=False)
    (logs / "acceptance.log").write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "4 passed" in result.stdout
