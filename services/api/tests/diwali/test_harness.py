"""The acceptance runner must fail closed instead of blessing missing evidence."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def harness():
    path = ROOT / "scripts/verify_diwali.py"
    if not path.exists():
        pytest.fail("Executable V2.1 gate verifier is not implemented")
    spec = importlib.util.spec_from_file_location("verify_diwali", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_proof_requires_artifact(tmp_path):
    claimed = {"status": "PROVEN", "configured": True, "enabled": True}
    assert harness().proof_status("band", claimed, tmp_path, "tree") == "NOT_STARTED"
    claimed["artifact"] = "missing.json"
    assert harness().proof_status("band", claimed, tmp_path, "tree") != "PROVEN"
    receipt = {"provider": "band", "tested_tree_digest": "tree", "consumed": True,
               "observed_at": "2026-11-15T00:00:00Z", "source_run": "fake", "invocation": "fake",
               "configuration_digest": "fake", "evidence_digest": "fake"}
    (tmp_path / "missing.json").write_text(json.dumps(receipt))
    assert harness().proof_status("band", claimed, tmp_path, "tree") != "PROVEN"


def test_skips_cannot_pass(tmp_path):
    module = harness()
    path = tmp_path / "test_required.py"
    for source in [
        "import pytest\n@pytest.mark.skip(reason='missing')\ndef test_required(): pass\n",
        "import pytest\n@pytest.mark.xfail(reason='broken')\ndef test_required(): assert False\n",
        "import pytest\n@pytest.mark.xfail(reason='unexpected pass')\ndef test_required(): pass\n",
        "# zero tests\n",
        "def test_required(): assert False\n",
    ]:
        path.write_text(source)
        result = module.run_pytest([str(path)], tmp_path, tmp_path / "evidence")
        assert result["status"] == "FAIL", result
        assert Path(result["stdout_path"]).exists()
        assert "duration_seconds" in result


def test_missing_required_node_is_blocked(tmp_path):
    result = harness().run_pytest([str(tmp_path / "missing.py")], tmp_path, tmp_path / "evidence")
    assert result["status"] == "BLOCKED"


def test_deliberate_violation_changes_exit_status(tmp_path):
    path = tmp_path / "test_outcome.py"
    path.write_text("def test_outcome(): assert 'verified_match' == 'verified_match'\n")
    module = harness()
    assert module.run_pytest([str(path)], tmp_path, tmp_path / "pass")["status"] == "PASS"
    path.write_text("def test_outcome(): assert 'verified_match' == 'rejected'\n")
    assert module.run_pytest([str(path)], tmp_path, tmp_path / "fail")["status"] == "FAIL"


def test_baseline_integrity(tmp_path):
    module = harness()
    (tmp_path / "fixture").write_text("original")
    import hashlib
    digest = hashlib.sha256(b"original").hexdigest()
    baseline = {"fixture_digests": {"fixture": digest}, "protected_file_digests": {},
                "oracle_digests": {}, "lockfile_digests": {}}
    assert module.check_integrity(tmp_path, baseline) == []
    (tmp_path / "fixture").write_text("changed")
    assert module.check_integrity(tmp_path, baseline) == ["Changed protected input: fixture"]


def test_command_failure_keeps_evidence(tmp_path):
    module = harness()
    result = module.run_command([sys.executable, "-c", "print('observed failure'); raise SystemExit(7)"],
                                tmp_path, tmp_path / "command")
    assert result["status"] == "FAIL"
    assert result["exit_code"] == 7
    assert "observed failure" in Path(result["stdout_path"]).read_text()
    assert result["duration_seconds"] >= 0


def test_g3_cannot_pass_without_app_regressions(tmp_path):
    module = harness()
    folder = tmp_path / "harness/diwali"
    folder.mkdir(parents=True)
    (folder / "baseline.json").write_text(json.dumps({"checks": [{"exit_code": 0}]}))
    (tmp_path / "test_acceptance.py").write_text("def test_acceptance(): assert True\n")
    (folder / "acceptance.json").write_text(json.dumps({"requirements": [],
        "gate_checks": {g: ["test_acceptance.py"] for g in ["G1", "G2", "G3"]}}))
    results = module.verify(tmp_path, "G3")
    assert results["G3"]["status"] == "FAIL"
    assert results["G3"]["regressions"][0]["exit_code"] != 0


def test_mutation_requires_assertion_failure_and_restores_source(tmp_path):
    module = harness()
    path = tmp_path / "decision.py"
    path.write_text("def allowed():\n    return False\n")
    original = path.read_bytes()
    test = tmp_path / "test_decision.py"
    test.write_text("from decision import allowed\ndef test_decision(): assert allowed() is False\n")
    result = module.mutation_probe(tmp_path, "decision.py", "return False", "return True",
                                   [str(test)], tmp_path / "probe")
    assert result["status"] == "PASS"
    assert result["observed_exit_code"] == 1
    assert path.read_bytes() == original
    broken = module.mutation_probe(tmp_path, "decision.py", "return False", "syntax error !",
                                   [str(test)], tmp_path / "bad-probe")
    assert broken["status"] != "PASS"
    assert path.read_bytes() == original


def test_reports_saved_at_frozen_evidence_paths(tmp_path):
    module = harness()
    module.write_reports(tmp_path, {"G1": {"status": "FAIL", "exit_code": 7}})
    path = tmp_path / "docs/evidence/diwali/v2.1/G1.json"
    assert json.loads(path.read_text())["exit_code"] == 7
    assert json.loads(path.with_name("gates.json").read_text())["G1"]["status"] == "FAIL"


