"""Bounded data-only auditor package. Local bytes never prove Finch delivery."""

import hashlib
import io
import json
import re
import zipfile
from urllib.parse import urlsplit

from app.config import ROOT
from app.diwali.lyzr_review import unique_object
from app.matching.recall import match_recall
from app.schemas import ProductInput, RecallRecord

NAME = "sueperman-recall-evidence-auditor"
FILES = frozenset({"SKILL.md", "rules.md", "examples.json", "LICENSE"})
RULES = ("services/api/app/matching/recall.py", "services/api/app/matching/normalize.py",
         "services/api/app/security/source_policy.py")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build_package():
    directory = ROOT / "skills" / NAME
    files = {name: (directory / name).read_bytes() for name in sorted(FILES)}
    manifest = {"name": NAME, "version": "1.0.0", "license": "MIT",
        "files": {name: sha(data) for name, data in files.items()},
        "rules": {name: sha((ROOT / name).read_bytes()) for name in RULES}}
    files["manifest.json"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return output.getvalue()


def load_package(data, expected_sha256, *, require_finch=False, delivery=None):
    if len(data) > 262144 or not re.fullmatch(r"[a-f0-9]{64}", expected_sha256) or sha(data) != expected_sha256:
        raise ValueError("Package pin mismatch or oversize archive")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            if (len(names) != len(set(names)) or set(names) != FILES | {"manifest.json"}
                    or sum(entry.file_size for entry in entries) > 262144
                    or any((entry.external_attr >> 16) & 0o170000 == 0o120000 for entry in entries)):
                raise ValueError("Unexpected path, hook, symlink or package size")
            content = {}
            for name in names:
                with archive.open(name) as member:
                    content[name] = member.read(262145)
                if len(content[name]) > 262144:
                    raise ValueError("Oversize package member")
        manifest = json.loads(content["manifest.json"], object_pairs_hook=unique_object)
        if (set(manifest) != {"name", "version", "license", "files", "rules"}
                or manifest["name"] != NAME or manifest["version"] != "1.0.0"
                or set(manifest["files"]) != FILES or set(manifest["rules"]) != set(RULES)
                or any(sha(content[name]) != expected for name, expected in manifest["files"].items())
                or any(sha((ROOT / name).read_bytes()) != expected for name, expected in manifest["rules"].items())):
            raise ValueError("Package identity or rule pin mismatch")
        markdown = content["SKILL.md"].decode()
        all_text = b"\n".join(content.values()).decode()
        if re.search(r"\b(?:agk_|sk_live_|sk-proj-)[A-Za-z0-9_-]{10,}|Bearer\s+[A-Za-z0-9_-]{12,}", all_text):
            raise ValueError("Potential credential in package")
        if require_finch:
            source = urlsplit((delivery or {}).get("listing_url", ""))
            if (source.scheme != "https" or source.hostname not in {"www.finchtech.ai", "finchtech.ai"}
                    or not source.path.strip("/") or source.username or source.password
                    or (delivery or {}).get("package_sha256") != expected_sha256
                    or delivery.get("version") != manifest["version"] or manifest["license"] == "UNLICENSED"):
                raise ValueError("Reviewed Finch delivery and license required")
        return {"name": NAME, "version": manifest["version"], "license": manifest["license"],
            "sha256": expected_sha256, "markdown": markdown,
            "examples": json.loads(content["examples.json"], object_pairs_hook=unique_object),
            "mode": "finch_delivery_declared" if require_finch else "local_authored",
            "listing_url": delivery["listing_url"] if require_finch else None}
    except (zipfile.BadZipFile, UnicodeError, KeyError, TypeError, OSError) as exc:
        raise ValueError("Invalid data-only package") from exc


def check_examples(skill):
    record = RecallRecord.model_validate_json((ROOT / "demo/recall_fixture.json").read_text())
    results = []
    for example in skill["examples"]:
        product = ProductInput(product_name="Power bank", brand="NEWDERY", model_number=example["purchase_model"])
        outcome = match_recall(product, record).status
        if outcome != example["expected"]:
            raise ValueError("Auditor example contradicts authoritative matcher")
        results.append(outcome)
    return results


def load_configured_skill(settings):
    from pathlib import Path

    if not settings.finch_delivery_file or not settings.finch_skill_path or not settings.finch_skill_sha256:
        raise ValueError("Reviewed Finch delivery metadata required")
    package_path, delivery_path = Path(settings.finch_skill_path), Path(settings.finch_delivery_file)
    if package_path.stat().st_size > 262144 or delivery_path.stat().st_size > 65536:
        raise ValueError("Oversized Finch delivery")
    delivery = json.loads(delivery_path.read_text(), object_pairs_hook=unique_object)
    return load_package(package_path.read_bytes(), settings.finch_skill_sha256,
                        require_finch=True, delivery=delivery)
