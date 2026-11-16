import hashlib

import httpx
import pytest


def test_adal_denies_tools_that_can_execute_mutate_or_fetch():
    from app.collaboration.adapters import adal_tool_allowed

    for name in ["shell", "bash", "write_file", "read_file", "web_fetch", "browser", "unknown"]:
        assert adal_tool_allowed(name, {}) is False
    assert adal_tool_allowed("read_case_evidence", {"source_ref": "26-792"}, ["26-792"]) is True
    assert adal_tool_allowed("read_case_evidence", {"source_ref": "invented"}, ["26-792"]) is False


def test_skill_integrity_requires_review_license_delivery_and_exact_bytes():
    from app.collaboration.adapters import SkillManifest, verified_skill

    data = b"Fixed challenge checklist"
    manifest = SkillManifest(
        identity="test-package",
        version="1",
        license="MIT",
        package_sha256=hashlib.sha256(data).hexdigest(),
        delivery_url="https://www.finchtech.ai/en/skills/test-package",
        review_record="reviewed fixture; not live proof",
    )
    assert verified_skill(data, manifest) == data.decode()
    with pytest.raises(ValueError):
        verified_skill(data + b"altered", manifest)


@pytest.mark.asyncio
async def test_agent37_exec_uses_pinned_command_and_rejects_failed_result():
    from app.collaboration.adapters import Agent37Scout

    requests = []

    def respond(request):
        requests.append(request)
        return httpx.Response(
            200, json={"exit_code": 1, "stdout": "", "stderr": "PRIVATE ERROR", "truncated": False}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        worker = Agent37Scout("test-key", "testinstance", "a" * 40, client)
        with pytest.raises(ValueError, match="Scout execution unavailable"):
            await worker.lookup(10)
    assert len(requests) == 1
    assert requests[0].url.host == "sandbox.agent37.app"
    assert "a" * 40 in requests[0].content.decode()
    assert "app.collaboration.scout_worker" in requests[0].content.decode()


def test_lyzr_output_rejects_unknown_prose_and_fabricated_citations():
    from app.collaboration.adapters import validate_builder

    with pytest.raises(ValueError):
        validate_builder({"message": "Guaranteed payment"}, "task", "case", "a" * 64, ["26-792"])
    data = {
        "task_id": "task",
        "case_id": "case",
        "revision": "a" * 64,
        "provider": "lyzr",
        "role": "builder",
        "mode": "live",
        "status": "completed",
        "findings": [],
        "source_refs": ["invented"],
    }
    with pytest.raises(ValueError):
        validate_builder(data, "task", "case", "a" * 64, ["26-792"])


def test_reviewed_zip_skill_loads_primary_document_without_extraction():
    import hashlib
    import io
    import zipfile

    from app.collaboration.adapters import SkillManifest, verified_skill

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("SKILL.md", "Check every supplied condition.")
        z.writestr("LICENSE", "Synthetic test license")
    data = archive.getvalue()
    manifest = SkillManifest(
        identity="synthetic-test-only",
        version="1",
        license="MIT",
        package_sha256=hashlib.sha256(data).hexdigest(),
        primary_sha256=hashlib.sha256(b"Check every supplied condition.").hexdigest(),
        delivery_url="https://www.finchtech.ai/synthetic-test-only",
        review_record="Synthetic test; not downloaded or live proof",
    )
    assert verified_skill(data, manifest) == "Check every supplied condition."
    with pytest.raises(ValueError):
        verified_skill(data + b"tampered", manifest)
