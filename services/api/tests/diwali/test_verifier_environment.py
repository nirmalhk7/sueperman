"""Gate regressions must consume their owned, controlled browser environment."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def verifier():
    spec = importlib.util.spec_from_file_location("environment_verifier", ROOT / "scripts/verify_diwali.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_command_receives_owned_server_addresses_without_enabling_paid_providers(tmp_path):
    module = verifier()
    command = [sys.executable, "-c", ("import os; "
        "assert os.environ['API_URL']=='http://127.0.0.1:45321'; "
        "assert os.environ['WEB_URL']=='http://127.0.0.1:45322'; "
        "assert os.environ['OPENAI_ENABLED']=='false'; print('controlled addresses reached child')")]
    try:
        result = module.run_command(command, tmp_path, tmp_path / "command", env_overrides={
            "API_URL": "http://127.0.0.1:45321", "WEB_URL": "http://127.0.0.1:45322"})
    except TypeError:
        pytest.fail("Gate command cannot consume the owned dynamic server environment")
    assert result["status"] == "PASS"
    assert "controlled addresses reached child" in Path(result["stdout_path"]).read_text()


def test_server_adapter_owns_fixture_lifetime_and_preserves_logs_on_body_failure(tmp_path):
    """A failing regression must release only its fixture resources and keep proof."""
    module = verifier()
    source = tmp_path / "services/api/tests/diwali/test_ui.py"
    source.parent.mkdir(parents=True)
    source.write_text('''from pathlib import Path
import pytest
@pytest.fixture
def browser_env(tmp_path_factory):
    folder=tmp_path_factory.mktemp("controlled")
    marker=folder/"owned-resource"
    marker.write_text("active")
    logs=folder/"logs"
    logs.mkdir()
    (logs/"api.log").write_text("controlled API retained")
    (logs/"web.log").write_text("controlled web retained")
    (logs/"build.log").write_text("copied frontend built")
    try:
        yield folder, {"API_URL":"http://127.0.0.1:45323", "WEB_URL":"http://127.0.0.1:45324", "OWNED_RESOURCE":str(marker)}, logs
    finally:
        marker.unlink()
''')
    evidence = tmp_path / "evidence"
    marker = None
    with pytest.raises(RuntimeError, match="regression failed"):
        try:
            with module.app_servers(tmp_path, evidence) as environment:
                assert environment["API_URL"] == "http://127.0.0.1:45323"
                marker = Path(environment["OWNED_RESOURCE"])
                assert marker.read_text() == "active"
                raise RuntimeError("regression failed")
        except OSError:
            pytest.fail("Gate server setup did not consume the controlled fixture")
    assert marker is not None and not marker.exists()
    assert (evidence / "api.log").read_text() == "controlled API retained"
    assert (evidence / "web.log").read_text() == "controlled web retained"
    assert (evidence / "build.log").read_text() == "copied frontend built"
    observed = json.loads((evidence / "environment.json").read_text())
    assert observed["mode"] == "controlled-offline"
    assert observed["api_url"] == "http://127.0.0.1:45323"
    assert observed["web_url"] == "http://127.0.0.1:45324"
