import socket
from pathlib import Path

import pytest


def test_launcher_restricts_files_environment_network_and_image(tmp_path):
    from app.collaboration.adal_sandbox import sandbox_command

    work = tmp_path / "work"
    bundle = tmp_path / "bundle"
    auth = tmp_path / "auth"
    for p in [work, bundle, auth]:
        p.mkdir()
    (bundle / "adal").write_text("synthetic runtime")
    command = sandbox_command("sha256:" + "a" * 64, work, bundle, auth, tmp_path / "bridge")
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges" in command
    assert "--pull=never" in command
    assert "--privileged" not in command
    assert not any("docker.sock" in x or "API_KEY" in x for x in command)
    assert command[-2:] == ["/opt/adal/adal", "--sdk-runtime"]
    with pytest.raises(ValueError, match="digest"):
        sandbox_command("latest", work, bundle, auth, tmp_path / "bridge")


def test_egress_rejects_wildcards_private_addresses_and_unlisted_hosts():
    from app.collaboration.adal_sandbox import validate_target

    public = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
    private = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", 443))]
    assert validate_target("api.example.org:443", {"api.example.org"}, lambda *a: public) == (
        "api.example.org",
        443,
    )
    for target, hosts, resolved in [
        ("evil.example:443", {"api.example.org"}, public),
        ("api.example.org:80", {"api.example.org"}, public),
        ("api.example.org:443", {"api.example.org"}, private),
        ("127.0.0.1:443", {"127.0.0.1"}, public),
        ("api.example.org:443", {"*.example.org"}, public),
    ]:
        with pytest.raises(ValueError):
            validate_target(target, hosts, lambda *a, result=resolved: result)


def test_runtime_bundle_fingerprint_changes_with_code(tmp_path):
    from app.collaboration.adal_sandbox import bundle_digest

    (tmp_path / "adal").write_bytes(b"first")
    first = bundle_digest(tmp_path)
    (tmp_path / "adal").write_bytes(b"second")
    assert bundle_digest(tmp_path) != first
    (tmp_path / "link").symlink_to(Path("/etc/passwd"))
    with pytest.raises(ValueError):
        bundle_digest(tmp_path)


def test_actual_container_denies_egress_mutation_and_backend_secrets(tmp_path, monkeypatch):
    import json
    import shutil
    import subprocess

    from app.collaboration.adal_sandbox import EgressBridge, sandbox_command

    if not shutil.which("docker"):
        pytest.skip("Docker required for actual OS isolation acceptance")
    image = subprocess.run(
        ["docker", "image", "inspect", "python:3.12-slim-bookworm", "--format", "{{.Id}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if image.returncode:
        pytest.skip("Pinned local Python runtime image required; test never pulls")
    work, bundle, auth, bridge = [tmp_path / n for n in ["work", "bundle", "auth", "bridge"]]
    for p in [work, bundle, auth, bridge]:
        p.mkdir()
    (auth / "synthetic-token").write_text("test-only")
    script = bundle / "adal"
    script.write_text("""#!/usr/local/bin/python
import os,socket,json
from pathlib import Path
checks={"backend_secret_absent":"UNRELATED_BACKEND_SECRET" not in os.environ,
        "repository_absent":not Path("/workspace/sueperman").exists()}
for name,path in [("root_readonly","/etc/sueperman-test"),("auth_readonly","/home/adal/.adal/mutation")]:
 try: Path(path).write_text("no"); checks[name]=False
 except OSError: checks[name]=True
Path("permitted-temporary-file").write_text("synthetic")
checks["workspace_writable"]=True
try: socket.create_connection(("203.0.113.1",443),timeout=1); checks["direct_network_denied"]=False
except OSError: checks["direct_network_denied"]=True
with socket.create_connection(("127.0.0.1",39081)) as client:
 client.sendall(b"CONNECT unrelated.example:443 HTTP/1.1\\r\\n\\r\\n")
 checks["unlisted_proxy_denied"]=b"403" in client.recv(100)
status=Path("/proc/self/status").read_text()
checks["no_new_privileges"]="NoNewPrivs:\\t1" in status
checks["no_capabilities"]="CapEff:\\t0000000000000000" in status
print(json.dumps(checks))
raise SystemExit(0 if all(checks.values()) else 1)
""")
    script.chmod(0o755)
    monkeypatch.setenv("UNRELATED_BACKEND_SECRET", "synthetic-must-not-cross-boundary")
    with EgressBridge(bridge / "proxy.sock", []):
        command = sandbox_command(
            image.stdout.strip(),
            work,
            bundle,
            auth,
            bridge,
            name="sueperman-isolation-test-" + tmp_path.name.lower().replace("_", "-"),
        )
        run = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    assert run.returncode == 0, run.stderr
    assert all(json.loads(run.stdout).values())


@pytest.mark.asyncio
async def test_real_sdk_and_isolated_launcher_deny_every_tool_request(tmp_path, monkeypatch):
    import asyncio
    import json
    import shutil
    import subprocess

    pytest.importorskip("adal_agent_sdk")
    from app.collaboration.adal_sandbox import bundle_digest
    from app.collaboration.contracts import CaseTask
    from app.collaboration.runtime_adapters import AdalSkeptic
    from app.config import ROOT

    if not shutil.which("docker"):
        pytest.skip("Docker required for SDK wire/OS isolation test")
    image = await asyncio.to_thread(
        subprocess.run,
        ["docker", "image", "inspect", "python:3.12-slim-bookworm", "--format", "{{.Id}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if image.returncode:
        pytest.skip("Local pinned image unavailable; no pull")
    bundle, auth = tmp_path / "bundle", tmp_path / "auth"
    bundle.mkdir()
    auth.mkdir()
    native = bundle / "adal"
    native.write_text("""#!/usr/local/bin/python
import json,sys
def emit(x): print(json.dumps(x),flush=True)
init=json.loads(input())
assert init["permission_mode"]=="default" and init["can_use_tool"]
assert "Bash" in init["disabled_default_tools"]
emit({"type":"ready","session_id":"synthetic-isolated-session"})
query=json.loads(input()); task=json.loads(query["input"])["task"]
for name in ["bash","write_file","fetch_url","custom_tool"]:
 emit({"type":"control_request","request_id":name,"request":{"subtype":"can_use_tool","tool_name":name,"input":{}}})
 reply=json.loads(input())
 assert reply["response"]["behavior"]=="deny"
result={"case_id":task["case_id"],"task_id":task["task_id"],"revision":task["revision"],"role":"skeptic","provider":"adal","mode":"live","status":"completed","findings":[{"code":"checklist_exhausted","source_ref":"26-792"}],"source_refs":["26-792"]}
emit({"type":"assistant.message.completed","message":{"content":json.dumps(result)}})
emit({"type":"command.completed"})
""")
    native.chmod(0o755)
    for key, value in {
        "ADAL_BUNDLE_DIR": str(bundle),
        "ADAL_BUNDLE_SHA256": bundle_digest(bundle),
        "ADAL_SANDBOX_IMAGE": image.stdout.strip(),
        "ADAL_AUTH_DIRECTORY": str(auth),
        "ADAL_ALLOWED_HOSTS": "",
    }.items():
        monkeypatch.setenv(key, value)
    task = CaseTask(
        case_id="synthetic",
        task_id="synthetic",
        revision="a" * 64,
        sender="scout",
        recipient="skeptic",
        task_kind="counterexample_review",
        deduplication_key="test",
        allowed_capabilities=["challenge_conditions"],
        source_refs=["26-792"],
        remaining_seconds=20,
        mode="live",
    )
    result = await AdalSkeptic(str(ROOT / "scripts/adal_isolated_runtime.py")).review(
        task, {}, "synthetic reviewed instruction"
    )
    assert result.provider_reference == "synthetic-isolated-session"
    assert "synthetic" in json.dumps(result.model_dump())  # Synthetic protocol fixture, not sponsor proof.


def test_builtin_launcher_preflight_requires_native_bundle_and_auth():
    import hashlib

    from app.collaboration.live import blockers
    from app.config import ROOT, Settings

    launcher = ROOT / "scripts/adal_isolated_runtime.py"
    settings = Settings(
        collaboration_live_enabled=True,
        adal_enabled=True,
        adal_isolation_verified=True,
        adal_runtime_path=str(launcher),
        adal_runtime_sha256=hashlib.sha256(launcher.read_bytes()).hexdigest(),
    )
    assert "adal" in blockers(settings)
