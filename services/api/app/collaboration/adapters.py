"""Bounded sponsor interfaces and reviewed Finch package verification; live proof is separate."""

import hashlib
import hmac
import io
import json
import re
import stat
import zipfile
from pathlib import PurePosixPath
from urllib.parse import urlsplit

import httpx
from pydantic import Field, field_validator

from app.collaboration.contracts import CaseResult, Strict
from app.schemas import RecallRecord


class SkillManifest(Strict):
    identity: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    license: str = Field(min_length=1, max_length=200)
    package_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    primary_document: str = Field(default="SKILL.md", min_length=1, max_length=200)
    primary_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    delivery_url: str = Field(max_length=2048)
    review_record: str = Field(min_length=1, max_length=2000)

    @field_validator("delivery_url")
    @classmethod
    def finch_delivery(cls, value):
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in {"finchtech.ai", "www.finchtech.ai"}
            or parsed.username
            or parsed.password
            or parsed.port not in {None, 443}
        ):
            raise ValueError("Verified Finch delivery URL required")
        return value


def verified_skill(data: bytes, manifest: SkillManifest) -> str:
    """Hash reviewed bytes before consuming them; never extract archives or execute package code."""
    if len(data) > 128_000 or not hmac.compare_digest(
        hashlib.sha256(data).hexdigest(), manifest.package_sha256
    ):
        raise ValueError("Skill package changed or exceeds size limit")
    if zipfile.is_zipfile(io.BytesIO(data)):
        if not manifest.primary_sha256:
            raise ValueError("Archive requires a reviewed primary document hash")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 32 or sum(e.file_size for e in entries) > 256_000:
                raise ValueError("Skill archive exceeds review budget")
            if len({e.filename for e in entries}) != len(entries):
                raise ValueError("Ambiguous duplicate archive entry")
            for entry in entries:
                path = PurePosixPath(entry.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or "\\" in entry.filename
                    or stat.S_ISLNK(entry.external_attr >> 16)
                ):
                    raise ValueError("Unsafe skill archive path")
            try:
                data = archive.read(manifest.primary_document)
            except (KeyError, RuntimeError, zipfile.BadZipFile):
                raise ValueError("Skill primary document unavailable") from None
    if manifest.primary_sha256 and not hmac.compare_digest(
        hashlib.sha256(data).hexdigest(), manifest.primary_sha256
    ):
        raise ValueError("Skill primary document changed")
    return data.decode("utf-8", errors="strict")


def adal_tool_allowed(name: str, arguments: dict, source_refs=()) -> bool:
    # A custom in-memory evidence reader is the only proposed tool. Default tools
    # must additionally be disabled in the eventual SDK runtime and OS sandbox.
    return (
        name == "read_case_evidence"
        and set(arguments) == {"source_ref"}
        and arguments["source_ref"] in source_refs
    )


def validate_builder(data, task_id, case_id, revision, sources):
    result = CaseResult.model_validate(data)
    if (result.task_id, result.case_id, result.revision, result.role, result.provider, result.mode) != (
        task_id,
        case_id,
        revision,
        "builder",
        "lyzr",
        "live",
    ):
        raise ValueError("Unexpected Builder response identity")
    if not set(result.source_refs).issubset(sources):
        raise ValueError("Builder fabricated citations")
    if any(f.source_ref and f.source_ref not in result.source_refs for f in result.findings):
        raise ValueError("Builder finding cites unavailable evidence")
    return result


class Agent37Scout:
    """One fixed read worker; no generated shell, allocation, credentials in worker or retry.

    Operator must provision /app/sueperman at the exact reviewed Git revision and
    validate sandbox network/process policy separately before enabling a live harness.
    """

    def __init__(self, token: str, instance: str, worker_revision: str, client=None):
        if not token or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", instance):
            raise ValueError("Agent37 configuration required")
        if not re.fullmatch(r"[a-f0-9]{40}", worker_revision):
            raise ValueError("Pinned worker revision required")
        self.token, self.instance, self.revision, self.client = token, instance, worker_revision, client

    async def lookup(self, remaining_seconds: float) -> list[RecallRecord]:
        if remaining_seconds <= 0:
            raise ValueError("Scout deadline exhausted")
        if self.client is None:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                return await self._lookup(client, remaining_seconds)
        return await self._lookup(self.client, remaining_seconds)

    async def _lookup(self, client, remaining):
        command = (
            'cd /app/sueperman && test "$(git rev-parse HEAD)" = '
            + self.revision
            + " && PYTHONPATH=services/api services/api/.venv/bin/python -m app.collaboration.scout_worker"
        )
        try:
            response = await client.post(
                f"https://sandbox.agent37.app/v1/instances/{self.instance}/exec",
                headers={"X-Agent37-Key": self.token},
                json={"command": command},
                timeout=min(remaining, 75),
                follow_redirects=False,
            )
            response.raise_for_status()
            data = response.json()
            if data.get("exit_code") != 0 or data.get("truncated") or len(data.get("stdout", "")) > 100_000:
                raise ValueError("Invalid worker result")
            result = json.loads(data["stdout"])
            if not isinstance(result, list) or len(result) > 1:
                raise ValueError("Unsupported worker output")
            records = [RecallRecord.model_validate(record) for record in result]
            if any(r.reference != "26-792" or r.mode != "live" for r in records):
                raise ValueError("Unsupported source")
            return records
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise ValueError("Scout execution unavailable") from None
