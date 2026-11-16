"""Procedural auditor bytes are pinned, bounded and never executable authority."""

import hashlib
import importlib
import io
import json
import zipfile

import pytest


def auditor():
    try:
        return importlib.import_module("app.diwali.finch_skill")
    except ModuleNotFoundError:
        pytest.fail("Recall Evidence Auditor package/loader is not implemented")


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as zipped:
        for name, value in files:
            zipped.writestr(name, value)
    return output.getvalue()


def test_authored_package_is_repeatable_and_loaded_as_local_procedure_only():
    module = auditor()
    first = module.build_package()
    assert first == module.build_package()
    pin = hashlib.sha256(first).hexdigest()
    skill = module.load_package(first, pin)
    assert skill["name"] == "sueperman-recall-evidence-auditor"
    assert skill["version"] == "1.0.0"
    assert skill["mode"] == "local_authored"
    assert skill["sha256"] == pin
    assert "ZHX-PB23" in skill["markdown"]
    assert "cannot override" in skill["markdown"]
    assert module.check_examples(skill) == ["verified_match", "rejected", "needs_review", "rejected", "rejected"]


@pytest.mark.parametrize("fault", ["hash", "traversal", "hook", "duplicate", "oversize", "symlink"])
def test_tampered_or_executable_archive_is_rejected(fault):
    module = auditor()
    if fault == "hash":
        with pytest.raises(ValueError):
            module.load_package(module.build_package(), "0" * 64)
        return
    with zipfile.ZipFile(io.BytesIO(module.build_package())) as original:
        files = [(name, original.read(name)) for name in original.namelist()]
    if fault == "traversal":
        files.append(("../SKILL.md", b"bad"))
    elif fault == "hook":
        files.append(("run.py", b"print('bad')"))
    elif fault == "duplicate":
        # Identical duplicate content preserves every manifest hash: only the
        # duplicate-entry defense rejects it.
        files.append(("SKILL.md", dict(files)["SKILL.md"]))
    elif fault == "oversize":
        content = dict(files)
        content["SKILL.md"] = b"x" * 262145
        manifest = json.loads(content["manifest.json"])
        manifest["files"]["SKILL.md"] = hashlib.sha256(content["SKILL.md"]).hexdigest()
        content["manifest.json"] = json.dumps(manifest).encode()
        files = list(content.items())
    stream = io.BytesIO()
    def write_archive():
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
            for name, value in files:
                if fault == "symlink" and name == "SKILL.md":
                    info = zipfile.ZipInfo(name)
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                    zipped.writestr(info, value)
                else:
                    zipped.writestr(name, value)
    if fault == "duplicate":
        with pytest.warns(UserWarning, match="Duplicate name"):
            write_archive()
    else:
        write_archive()
    data = stream.getvalue()
    with pytest.raises(ValueError):
        module.load_package(data, hashlib.sha256(data).hexdigest())


def test_local_bytes_cannot_claim_finch_delivery():
    module = auditor()
    data = module.build_package()
    with pytest.raises(ValueError, match="Finch delivery"):
        module.load_package(data, hashlib.sha256(data).hexdigest(), require_finch=True)


def test_configured_finch_requires_actual_reviewed_delivery_metadata(tmp_path):
    from types import SimpleNamespace

    module = auditor()
    data = module.build_package()
    path = tmp_path / "auditor.zip"
    path.write_bytes(data)
    config = SimpleNamespace(finch_skill_path=str(path), finch_skill_sha256=hashlib.sha256(data).hexdigest(),
                             finch_delivery_file="")
    if not hasattr(module, "load_configured_skill"):
        pytest.fail("Enabled Finch does not enforce a reviewed delivery before reviewer use")
    with pytest.raises(ValueError, match="delivery"):
        module.load_configured_skill(config)


def test_owner_approved_skill_license_is_in_package_not_only_listing():
    module = auditor()
    data = module.build_package()
    skill = module.load_package(data, hashlib.sha256(data).hexdigest())
    assert skill["license"] == "MIT"
    with zipfile.ZipFile(io.BytesIO(data)) as zipped:
        assert zipped.read("LICENSE").decode().startswith("MIT License")
