"""Configured live role factory. No network/paid call happens during preflight."""

import hashlib
import importlib.util
import re
from pathlib import Path

from app.collaboration.adapters import Agent37Scout, SkillManifest, verified_skill
from app.collaboration.contracts import CaseResult, Finding
from app.collaboration.ledger import digest
from app.collaboration.runtime_adapters import AdalSkeptic, LyzrBuilder
from app.schemas import RecallRecord
from app.security.source_policy import official_cpsc


def load_skill(settings):
    manifest = SkillManifest.model_validate_json(Path(settings.finch_manifest_path).read_text())
    data = Path(settings.finch_package_path).read_bytes()
    return manifest, verified_skill(data, manifest)


def blockers(settings):
    blocked = {}
    if not settings.collaboration_live_enabled:
        return {
            p: "Global live-team kill switch is off" for p in ["band", "agent37", "adal", "finch", "lyzr"]
        }
    if (
        not settings.band_enabled
        or not settings.band_room_id
        or set(settings.band_identities) != {"controller", "scout", "skeptic", "builder"}
        or set(settings.band_api_keys) != set(settings.band_identities)
        or any(not key.get_secret_value() for key in settings.band_api_keys.values())
        or len(set(settings.band_identities.values())) != 4
        or importlib.util.find_spec("band") is None
    ):
        blocked["band"] = "BAND SDK, room and four distinct identities/keys required"
    if (
        not settings.agent37_enabled
        or not settings.agent37_api_key.get_secret_value()
        or not settings.agent37_instance_id
        or not settings.agent37_worker_revision
        or not settings.agent37_isolation_verified
    ):
        blocked["agent37"] = "Agent37 key, pinned worker instance and verified isolation required"
    if (
        not settings.adal_enabled
        or not settings.adal_isolation_verified
        or not settings.adal_runtime_path
        or importlib.util.find_spec("adal_agent_sdk") is None
    ):
        blocked["adal"] = "Authenticated AdaL SDK/isolated launcher and verified policy required"
    else:
        try:
            if (
                hashlib.sha256(Path(settings.adal_runtime_path).read_bytes()).hexdigest()
                != settings.adal_runtime_sha256
            ):
                blocked["adal"] = "AdaL isolated launcher hash differs from reviewed configuration"
            if Path(settings.adal_runtime_path).name == "adal_isolated_runtime.py":
                from app.collaboration.adal_sandbox import EgressBridge, bundle_digest

                if (
                    not settings.adal_bundle_dir
                    or not settings.adal_auth_directory
                    or not Path(settings.adal_auth_directory).is_dir()
                    or not re.fullmatch(r"sha256:[a-f0-9]{64}", settings.adal_sandbox_image)
                    or not settings.adal_allowed_hosts
                    or bundle_digest(settings.adal_bundle_dir) != settings.adal_bundle_sha256
                ):
                    raise ValueError("Incomplete native sandbox setup")
                EgressBridge("/unused-preflight-socket", settings.adal_allowed_hosts.split(","))
        except (OSError, ValueError):
            blocked["adal"] = (
                "Reviewed native bundle/image, scoped cached auth and exact runtime hosts required"
            )
    try:
        if not settings.finch_enabled:
            raise ValueError("disabled")
        load_skill(settings)
    except (ValueError, OSError):
        blocked["finch"] = "Reviewed Finch manifest and exact delivered package bytes required"
    try:
        if not settings.lyzr_enabled:
            raise ValueError("disabled")
        LyzrBuilder(
            settings.lyzr_api_key.get_secret_value(),
            settings.lyzr_chat_url,
            settings.lyzr_agent_id,
            settings.lyzr_user_id,
            settings.lyzr_api_profile,
        )
    except ValueError:
        blocked["lyzr"] = "Lyzr key, Studio agent and verified workspace v3 endpoint/profile required"
    return blocked


class LiveTeam:
    """Separate BAND identities delegate to the actual sponsor runtimes."""

    def __init__(self, settings):
        from app.collaboration.band_runtime import BandSession

        self.settings = settings
        self.manifest, self.skill = load_skill(settings)
        self.skill_hash = self.manifest.package_sha256
        self.scout = Agent37Scout(
            settings.agent37_api_key.get_secret_value(),
            settings.agent37_instance_id,
            settings.agent37_worker_revision,
        )
        self.skeptic = AdalSkeptic(settings.adal_runtime_path)
        self.builder = LyzrBuilder(
            settings.lyzr_api_key.get_secret_value(),
            settings.lyzr_chat_url,
            settings.lyzr_agent_id,
            settings.lyzr_user_id,
            settings.lyzr_api_profile,
        )
        self.transport = BandSession(
            settings.band_room_id,
            settings.band_identities,
            {r: k.get_secret_value() for r, k in settings.band_api_keys.items()},
            {"scout": self.source, "skeptic": self.challenge, "builder": self.build},
        )

    async def __aenter__(self):
        await self.transport.__aenter__()
        return self

    async def __aexit__(self, *args):
        await self.transport.__aexit__(*args)

    async def request(self, task, context):
        return await self.transport.request(task, context)

    async def source(self, task, context):
        records = await self.scout.lookup(task.remaining_seconds)
        if len(records) != 1 or not official_cpsc(records[0].official_url):
            raise ValueError("Supported official source unavailable")
        result = CaseResult(
            task_id=task.task_id,
            case_id=task.case_id,
            revision=task.revision,
            provider="agent37",
            role="scout",
            mode="live",
            status="completed",
            findings=[Finding(code="candidate", source_ref="26-792")],
            source_refs=["26-792"],
            provider_reference=self.settings.agent37_instance_id,
        )
        return {
            "result": result.model_dump(mode="json"),
            "records": [r.model_dump(mode="json") for r in records],
            "execution": {
                "instance": self.settings.agent37_instance_id,
                "worker_revision": self.settings.agent37_worker_revision,
                "exit_code": 0,
                "normalized_result_hash": digest([r.model_dump(mode="json") for r in records]),
            },
        }

    async def challenge(self, task, context):
        result = await self.skeptic.review(task, context, self.skill)
        return {"result": result.model_dump(mode="json"), "skill_hash": self.skill_hash}

    async def build(self, task, context):
        result = await self.builder.review(task, context)
        return {"result": result.model_dump(mode="json")}


def source_records(output):
    records = [RecallRecord.model_validate(r) for r in output.get("records", [])]
    if len(records) != 1 or any(
        r.reference != "26-792" or r.mode != "live" or not official_cpsc(r.official_url) for r in records
    ):
        raise ValueError("Unsupported live source output")
    return records
