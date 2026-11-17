"""Run the selected V2.1 gate with saved, unskipped executable evidence."""

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from contextlib import contextmanager
from pathlib import Path
from time import monotonic
from urllib.error import URLError
from urllib.request import urlopen

GATES = [f"G{i}" for i in range(10)]


def offline_environment():
    env = os.environ | {"SENTRY_DSN": "", "SENTRY_AUTH_TOKEN": "", "NEXT_PUBLIC_SENTRY_DSN": "",
                       "P1_LIVE_E2E": "0",
                       "PYTHONDONTWRITEBYTECODE": "1",
                       "API_URL": "http://localhost:8000", "WEB_URL": "http://localhost:3012",
                       "NEXT_PUBLIC_API_BASE_URL": "http://localhost:8000",
                       "FRONTEND_ORIGIN": "http://localhost:3012"}
    for key in ("DIWALI_LIVE_AUTHORIZED", "BAND_ENABLED", "LYZR_ENABLED", "FINCH_ENABLED", "AGENT37_ENABLED",
                "CPSC_LIVE_ENABLED", "OPENAI_ENABLED", "OPENAI_RECEIPT_ENABLED", "GEMINI_ENABLED",
                "BRIGHTDATA_ENABLED", "SYSTEM_ONE_ENABLED", "SETTLEMENT_LIVE_ENABLED"):
        env[key] = "false"
    return env


def source_tree_digest(root):
    paths = []
    for directory in ("services/api/app", "services/api/tests", "apps/web/app", "apps/web/lib",
                      "apps/web/components", "apps/web/tests", "scripts", "demo", "harness/diwali"):
        paths.extend(p for p in (root / directory).rglob("*") if p.is_file()
                     and "__pycache__" not in p.parts and p.name != "handoff.json")
    paths.extend(root / name for name in ("Makefile", "services/api/pyproject.toml", "services/api/uv.lock",
                 "apps/web/package.json", "apps/web/pnpm-lock.yaml", "apps/web/next.config.ts", "apps/web/tsconfig.json"))
    sha = hashlib.sha256()
    for path in sorted(set(paths)):
        if path.is_file():
            sha.update(str(path.relative_to(root)).encode())
            sha.update(path.read_bytes())
    return sha.hexdigest()


def run_command(command, root, evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    started = monotonic()
    result = {"command": command, "status": "BLOCKED", "exit_code": None,
              "stdout_path": str(evidence / "stdout.log"), "stderr_path": str(evidence / "stderr.log")}
    try:
        process = subprocess.run(command, cwd=root, env=offline_environment(), capture_output=True,
                                 text=True, timeout=360, check=False)
        Path(result["stdout_path"]).write_text(process.stdout)
        Path(result["stderr_path"]).write_text(process.stderr)
        result.update(exit_code=process.returncode, status="PASS" if process.returncode == 0 else "FAIL")
    except (OSError, subprocess.TimeoutExpired) as exc:
        Path(result["stderr_path"]).write_text(type(exc).__name__)
        result["blocker"] = type(exc).__name__
    result["duration_seconds"] = monotonic() - started
    return result


@contextmanager
def app_servers(root, evidence):
    """Never attach to or stop an existing process; busy required ports block proof."""
    for port in (8000, 3012):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))
    evidence.mkdir(parents=True, exist_ok=True)
    processes, streams = [], []
    with tempfile.TemporaryDirectory(prefix="sueperman-diwali-") as folder:
        env = offline_environment() | {"DATABASE_URL": f"sqlite:///{folder}/app.db", "DIWALI_ENABLED": "true",
                                       "PYTHONPATH": str(root / "services/api")}
        try:
            for name, command, url in [
                ("api", [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
                 "http://localhost:8000/api/health"),
                ("web", ["node", str(root / "apps/web/node_modules/next/dist/bin/next"), "start", "--hostname",
                         "127.0.0.1", "--port", "3012"], "http://localhost:3012"),
            ]:
                stream = (evidence / f"{name}.log").open("w")
                streams.append(stream)
                process = subprocess.Popen(command, cwd=root / "apps/web", env=env, stdout=stream,
                                           stderr=stream, start_new_session=True)
                processes.append(process)
                deadline = monotonic() + 60
                while True:
                    try:
                        with urlopen(url, timeout=2) as response:
                            if response.status == 200:
                                break
                    except (URLError, TimeoutError):
                        if process.poll() is not None or monotonic() > deadline:
                            raise RuntimeError(f"Task-owned {name} server did not become ready") from None
                        time.sleep(0.2)
            yield
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


def run_app_checks(root):
    evidence = root / "docs/evidence/diwali/v2.1/regressions"
    results = [run_command(["make", target], root, evidence / target)
               for target in ("test", "lint", "typecheck", "build")]
    if results[-1]["status"] != "PASS":
        results.append({"status": "BLOCKED", "blocker": "Build prerequisite for smoke/e2e did not pass"})
        return results
    try:
        with app_servers(root, evidence / "servers"):
            results.extend(run_command(["make", target], root, evidence / target) for target in ("smoke", "e2e"))
    except (OSError, RuntimeError) as exc:
        results.append({"status": "BLOCKED", "blocker": str(exc)})
    return results


def mutation_probe(root, name, before, after, nodes, evidence):
    path = root / name
    if not path.is_file() or path.read_text().count(before) != 1:
        return {"status": "BLOCKED", "blocker": f"Mutation target changed: {name}"}
    original = path.read_bytes()
    try:
        path.write_text(original.decode().replace(before, after, 1))
        observed = run_pytest(nodes, root, evidence)
        result = {"status": "FAIL", "target": name, "before": before, "after": after,
                  "observed_exit_code": observed["exit_code"], "check": observed}
        report = evidence / "pytest.xml"
        if report.exists():
            xml = ET.parse(report).getroot()
            if (observed["exit_code"] == 1 and xml.findall(".//failure")
                    and not xml.findall(".//error") and not xml.findall(".//skipped")):
                result["status"] = "PASS"
        return result
    finally:
        path.write_bytes(original)


def run_mutation_checks(root):
    evidence = root / "docs/evidence/diwali/v2.1/mutations"
    mutations = [
        ("pb23", "services/api/app/matching/recall.py",
         "model in [normalize_model(m) for m in recall.models] if model and recall.models else None",
         "True if model and recall.models else None",
         "services/api/tests/diwali/test_local_core.py::test_five_golden_outcomes"),
        ("unknown", "services/api/app/diwali/core.py",
         'outcome="needs_review", question_field="model_number"',
         'outcome="verified_match", question_field="model_number"',
         "services/api/tests/diwali/test_local_core.py::test_missing_purchase_model"),
        ("approval", "services/api/app/api/claims.py",
         'if packet.payload["status"] not in {"approved_local", "exported"}:', "if False:",
         "services/api/tests/diwali/test_api.py::test_unapproved_export"),
        ("duplicate", "services/api/app/diwali/core.py",
         'raise ValueError("Conflicting message ID reuse")\n        return state, ()',
         'raise ValueError("Conflicting message ID reuse")\n        return replace(state, revision=state.revision + 1), ()',
         "services/api/tests/diwali/test_reducer.py::test_duplicate_delivery"),
        ("provider-failure", "services/api/app/diwali/coordinator.py",
         'run.status = "partial" if surviving_results(session, run_id) else "failed"', 'run.status = "completed"',
         "services/api/tests/diwali/test_failures.py::test_malformed_result_closes_case_without_packet"),
        ("false-band", "services/api/app/api/runs.py", '"actual_transport": "local"', '"actual_transport": "band"',
         "services/api/tests/diwali/test_api.py::test_provenance"),
    ]
    results = []
    with tempfile.TemporaryDirectory(prefix="sueperman-mutations-") as folder:
        isolated = Path(folder)
        for directory in ("services/api/app", "services/api/tests", "demo", "harness/diwali"):
            source = root / directory
            if not source.exists():
                return [{"status": "BLOCKED", "blocker": "Mutation source tree missing"}]
            shutil.copytree(source, isolated / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copy2(root / "services/api/pyproject.toml", isolated / "services/api/pyproject.toml")
        for label, name, before, after, node in mutations:
            result = mutation_probe(isolated, name, before, after, [node], evidence / label)
            result["mutation"] = label
            results.append(result)
    return results


def preserved_extension(data, expected, extension):
    """Only exact reviewed insertions may differ from the original frozen bytes."""
    try:
        if (extension["baseline_sha256"] != expected
                or hashlib.sha256(data).hexdigest() != extension["extended_sha256"]):
            return False
        previous_end = 0
        insertions = extension["insertions"]
        if not insertions:
            return False
        for addition in insertions:
            offset, length = addition["offset"], addition["length"]
            if (type(offset) is not int or type(length) is not int or length <= 0
                    or offset < previous_end or offset + length > len(data)
                    or hashlib.sha256(data[offset:offset + length]).hexdigest() != addition["sha256"]):
                return False
            previous_end = offset + length
        for addition in reversed(insertions):
            offset, length = addition["offset"], addition["length"]
            data = data[:offset] + data[offset + length:]
        return hashlib.sha256(data).hexdigest() == expected
    except (KeyError, TypeError, ValueError):
        return False


def check_integrity(root, baseline):
    try:
        manifest = json.loads((root / "harness/diwali/integrity-extensions.json").read_text())
        extensions = manifest["files"] if manifest["version"] == 1 else {}
    except (OSError, ValueError, KeyError, TypeError):
        extensions = {}
    failures = []
    for group in ("protected_file_digests", "fixture_digests", "lockfile_digests", "oracle_digests"):
        for name, expected in baseline.get(group, {}).items():
            path = root / name
            data = path.read_bytes() if path.is_file() else None
            actual = hashlib.sha256(data).hexdigest() if data is not None else None
            allowed = (group in {"protected_file_digests", "lockfile_digests"}
                       and name in {"README.md", ".env.example", "services/api/uv.lock",
                                    "services/api/app/api/collaborations.py",
                                    "services/api/app/collaboration/controller.py",
                                    "services/api/app/collaboration/ledger.py"}
                       and data is not None and isinstance(extensions, dict)
                       and preserved_extension(data, expected, extensions.get(name, {})))
            if actual != expected and not allowed:
                failures.append(f"Changed protected input: {name}")
    return failures


def proof_status(provider, record, root, tree_digest):
    artifact = record.get("artifact")
    if not artifact:
        return "NOT_STARTED"
    path = (root / artifact).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        return "IMPLEMENTED_UNVERIFIED"
    try:
        receipt = json.loads(path.read_text())
    except (ValueError, OSError):
        return "IMPLEMENTED_UNVERIFIED"
    # A receipt-shaped assertion is not an observed provider capture. Provider gates
    # must add their locked artifact validator before any PROVEN path can exist.
    if receipt.get("provider") != provider or receipt.get("tested_tree_digest") != tree_digest:
        return "IMPLEMENTED_UNVERIFIED"
    return "PARTIAL"


def run_pytest(nodes, root, evidence):
    evidence.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, "-m", "pytest", *nodes, "-q", "--strict-markers", "-o", "xfail_strict=true",
               f"--junitxml={evidence / 'pytest.xml'}"]
    result = {"command": command, "status": "BLOCKED", "exit_code": None,
              "duration_seconds": 0, "stdout_path": str(evidence / "stdout.log"),
              "stderr_path": str(evidence / "stderr.log")}
    if not nodes or any(not (root / node.split("::")[0]).is_file() for node in nodes):
        result["blocker"] = "Required test node is missing"
        return result
    started = monotonic()
    env = offline_environment()
    try:
        process = subprocess.run(
            command, cwd=root, env=env, capture_output=True, text=True, timeout=180, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["blocker"] = type(exc).__name__
        return result
    result.update(exit_code=process.returncode, duration_seconds=monotonic() - started)
    Path(result["stdout_path"]).write_text(process.stdout)
    Path(result["stderr_path"]).write_text(process.stderr)
    result["status"] = "FAIL"
    try:
        report = ET.parse(evidence / "pytest.xml").getroot()
        tests = report.findall(".//testcase")
        result["tests"] = len(tests)
        if (process.returncode == 0 and tests
                and not report.findall(".//skipped") and not report.findall(".//failure")
                and not report.findall(".//error")):
            result["status"] = "PASS"
    except (ET.ParseError, OSError):
        pass
    return result


def verify(root, through):
    folder = root / "harness/diwali"
    baseline = json.loads((folder / "baseline.json").read_text())
    acceptance = json.loads((folder / "acceptance.json").read_text())
    failures = check_integrity(root, baseline)
    results = {"G0": {"status": "FAIL" if failures else "PASS", "failures": failures,
                      "baseline_checks": baseline["checks"]}}
    if not failures and any(c["exit_code"] != 0 for c in baseline["checks"]):
        results["G0"]["status"] = "BLOCKED"
    for gate in GATES[1:GATES.index(through) + 1]:
        if any(r["status"] != "PASS" for r in results.values()):
            results[gate] = {"status": "BLOCKED", "blocker": "Prerequisite gate did not pass"}
            continue
        nodes = list(acceptance["gate_checks"].get(gate, []))
        nodes += [r["node"] for r in acceptance["requirements"] if r["gate"] == gate]
        nodes = list(dict.fromkeys(nodes))
        results[gate] = run_pytest(nodes, root, root / "docs/evidence/diwali/v2.1" / gate)
        if gate == "G3" and results[gate]["status"] == "PASS":
            mutations = run_mutation_checks(root)
            results[gate]["mutations"] = mutations
            regressions = run_app_checks(root)
            results[gate]["regressions"] = regressions
            statuses = [r["status"] for r in [*mutations, *regressions]]
            results[gate]["status"] = "FAIL" if "FAIL" in statuses else "BLOCKED" if "BLOCKED" in statuses else "PASS"
    return results


def write_reports(root, results):
    evidence = root / "docs/evidence/diwali/v2.1"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "gates.json").write_text(json.dumps(results, indent=2) + "\n")
    for gate, result in results.items():
        (evidence / f"{gate}.json").write_text(json.dumps(result, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--through", choices=GATES, default="G3")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--live-provider", choices=["band", "lyzr", "finch", "agent37", "adal"])
    args = parser.parse_args()
    if args.live_provider or not args.offline:
        print("BLOCKED: live gates require a verified provider contract and explicit named-provider budget")
        return 2
    root = Path(__file__).resolve().parents[1]
    before = source_tree_digest(root)
    results = verify(root, args.through)
    after = source_tree_digest(root)
    if before != after:
        results[args.through]["status"] = "FAIL"
        results[args.through]["blocker"] = "Source/configuration changed during verification; rerun required"
    for result in results.values():
        result["tested_tree_digest"] = before
    write_reports(root, results)
    print(json.dumps(results, indent=2))
    statuses = [r["status"] for r in results.values()]
    return 1 if "FAIL" in statuses else 2 if "BLOCKED" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
