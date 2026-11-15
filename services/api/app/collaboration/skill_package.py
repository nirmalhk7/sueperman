"""Validate operator-reviewed Finch delivery pins; never execute downloaded content.

A passing hash check proves byte integrity against an operator's reviewed manifest,
not sponsor provenance. Live delivery and invocation receipts are separate gates.
"""

import hashlib
from typing import Literal

from pydantic import Field

from app.collaboration.contracts import Strict


class SkillManifest(Strict):
    delivery: Literal["finch"]
    chain_id: str = Field(min_length=1, max_length=100)
    skill_id: str = Field(min_length=1, max_length=200)
    version: str = Field(min_length=1, max_length=100)
    license: str = Field(min_length=1, max_length=200)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed: Literal[True]
    review_reference: str = Field(min_length=1, max_length=200)
    content_mode: Literal["public"]


def reviewed_package(content: bytes, manifest: dict) -> str:
    pin = SkillManifest(**manifest)
    if len(content) > 256000 or hashlib.sha256(content).hexdigest() != pin.sha256:
        raise ValueError("Skill package hash mismatch or oversized package")
    return content.decode("utf-8")
