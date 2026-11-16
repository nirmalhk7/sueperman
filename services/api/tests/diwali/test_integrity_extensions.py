"""Audited additions must preserve every frozen byte; arbitrary drift stays blocked."""

import hashlib
import json
import shutil

import pytest
from test_harness import ROOT, harness


@pytest.fixture
def audited_tree(tmp_path):
    baseline = json.loads((ROOT / "harness/diwali/baseline.json").read_text())
    names = ("README.md", ".env.example", "services/api/uv.lock", "services/api/app/api/collaborations.py")
    limited = {}
    for group in ("protected_file_digests", "lockfile_digests"):
        limited[group] = {n: h for n, h in baseline[group].items() if n in names}
    for name in (*names, "harness/diwali/integrity-extensions.json"):
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if (ROOT / name).is_file():
            shutil.copyfile(ROOT / name, target)
    return tmp_path, limited


def test_audited_p1_and_band_additions_pass_unchanged_frozen_baseline(audited_tree):
    root, baseline = audited_tree
    assert harness().check_integrity(root, baseline) == []


@pytest.mark.parametrize("name", ["README.md", ".env.example", "services/api/uv.lock",
                                  "services/api/app/api/collaborations.py"])
@pytest.mark.parametrize("change", ["original", "extension", "append", "delete"])
def test_only_exact_reviewed_additions_are_permitted(audited_tree, name, change):
    root, baseline = audited_tree
    path = root / name
    data = path.read_bytes()
    if change == "delete":
        path.unlink()
    elif change == "original":
        path.write_bytes(b"X" + data[1:])
    elif change == "extension":
        before = {"README.md": b"## V2 P1 additions", ".env.example": b"P1_ENABLED=false",
                  "services/api/uv.lock": b'version = "8.1.0"',
                  "services/api/app/api/collaborations.py": b"Current official source requires a new live review"}[name]
        assert data.count(before) == 1
        path.write_bytes(data.replace(before, b"tampered-extension", 1))
    else:
        path.write_bytes(data + b"\nunreviewed addition\n")
    assert f"Changed protected input: {name}" in harness().check_integrity(root, baseline)


def test_extension_manifest_cannot_bless_changed_fixture(audited_tree):
    root, baseline = audited_tree
    (root / "fixture").write_bytes(b"changed")
    baseline["fixture_digests"] = {"fixture": hashlib.sha256(b"original").hexdigest()}
    assert "Changed protected input: fixture" in harness().check_integrity(root, baseline)


def test_manifest_hash_update_cannot_hide_changed_original_bytes(audited_tree):
    root, baseline = audited_tree
    path = root / "README.md"
    path.write_bytes(b"X" + path.read_bytes()[1:])
    manifest_path = root / "harness/diwali/integrity-extensions.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["README.md"]["extended_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    assert "Changed protected input: README.md" in harness().check_integrity(root, baseline)


def test_manifest_wrong_insertion_cannot_hide_original_replacement(audited_tree):
    root, baseline = audited_tree
    manifest_path = root / "harness/diwali/integrity-extensions.json"
    manifest = json.loads(manifest_path.read_text())
    entry = manifest["files"]["README.md"]
    data = (root / "README.md").read_bytes()
    # Even a correctly hashed prefix cannot be substituted for the audited addition.
    length = entry["insertions"][0]["length"]
    entry["insertions"] = [{"offset": 0, "length": length,
                            "sha256": hashlib.sha256(data[:length]).hexdigest()}]
    manifest_path.write_text(json.dumps(manifest))
    assert "Changed protected input: README.md" in harness().check_integrity(root, baseline)
