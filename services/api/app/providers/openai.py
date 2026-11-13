"""Bounded System 1 decision role, implemented with OpenAI Responses structured output."""

import asyncio
import json

import httpx
from pydantic import BaseModel, ConfigDict

from app.providers.systemone import CHOICES, RouteDecision, RulesRouter
from app.schemas import MatchResult


class ChoiceOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    choice: str


class OpenAIDecisionRouter:
    provider_name = "openai"
    mode = "live"

    def __init__(self, token, model="gpt-6-luna", client=None):
        self.token, self.model, self.client = token, model, client

    async def route(self, result: MatchResult) -> RouteDecision:
        fallback = await RulesRouter().route(result)
        try:
            if not self.token:
                raise ValueError("OpenAI not configured")
            async with asyncio.timeout(10):
                if self.client is None:
                    async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                        choice = await self._choose(client, result)
                else:
                    choice = await self._choose(self.client, result)
            overridden = (
                choice == "produce_packet"
                and result.status != "verified_match"
                or choice == "reject_candidate"
                and result.status != "rejected"
            )
            return RouteDecision(
                choice=fallback.choice if overridden else choice,
                proposed_choice=choice,
                overridden=overridden,
                mode="openai",
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError, IndexError, TimeoutError):
            return fallback.model_copy(update={"mode": "rules_fallback"})

    async def _choose(self, client, result):
        state = {
            "hard_gate_status": result.status,
            "missing_conditions": [c.name for c in result.conditions if c.status == "unknown"],
        }
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.token}"},
            timeout=8,
            json={
                "model": self.model,
                "store": False,
                "reasoning": {"effort": "none"},
                "max_output_tokens": 128,
                "instructions": "Choose the safest next investigation step. Return one choice only. "
                + json.dumps(CHOICES),
                "input": json.dumps(state),
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "decision_route",
                        "strict": True,
                        "schema": {
                            "type": "object",
                            "properties": {"choice": {"type": "string", "enum": list(CHOICES)}},
                            "required": ["choice"],
                            "additionalProperties": False,
                        },
                    }
                },
            },
        )
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict) or body.get("status") != "completed":
            raise ValueError("Incomplete decision")
        output = body.get("output")
        if not isinstance(output, list):
            raise TypeError("Malformed decision output")
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                raise TypeError("Malformed output item")
            if item.get("type") != "message":
                continue
            content = item.get("content", [])
            if not isinstance(content, list) or any(not isinstance(part, dict) for part in content):
                raise ValueError("Malformed message content")
            texts.extend(part["text"] for part in content if part.get("type") == "output_text")
        if len(texts) != 1:
            raise ValueError("Missing structured choice or refusal")
        choice = ChoiceOutput.model_validate_json(texts[0]).choice
        if choice not in CHOICES:
            raise ValueError("Unknown choice")
        return choice
