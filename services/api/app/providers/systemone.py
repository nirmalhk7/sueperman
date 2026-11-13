from typing import Literal

import httpx
from pydantic import BaseModel

from app.schemas import MatchResult

CHOICES = {
    "inspect_more": "Need more official sources",
    "request_user_info": "Missing identifier",
    "produce_packet": "Verified hard-gates passed",
    "reject_candidate": "Official evidence excludes product",
}


class RouteDecision(BaseModel):
    choice: Literal["inspect_more", "request_user_info", "produce_packet", "reject_candidate"]
    mode: str = "rules"
    overridden: bool = False
    proposed_choice: str | None = None


class RulesRouter:
    provider_name = "rules"
    mode = "offline"

    async def route(self, result: MatchResult) -> RouteDecision:
        choice: Literal["inspect_more", "request_user_info", "produce_packet", "reject_candidate"] = (
            "produce_packet"
            if result.status == "verified_match"
            else "reject_candidate"
            if result.status == "rejected"
            else "request_user_info"
            if result.status == "needs_review"
            else "inspect_more"
        )
        return RouteDecision(choice=choice)


class SystemOneRouter:
    provider_name = "system_one"
    mode = "live"

    def __init__(self, token, model="decisions", client=None):
        self.token, self.model, self.client = token, model, client

    async def route(self, result: MatchResult) -> RouteDecision:
        fallback = await RulesRouter().route(result)
        if not self.token:
            return fallback.model_copy(update={"mode": "rules_fallback"})
        try:
            if self.client is None:
                async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
                    choice = await self._choose(client, result)
            else:
                choice = await self._choose(self.client, result)
            # Advisory model cannot contradict deterministic eligibility or exclusion.
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
                mode="system_one",
            )
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            return fallback.model_copy(update={"mode": "rules_fallback"})

    async def _choose(self, client, result):
        headers = {"Authorization": f"Bearer {self.token}"}
        response = await client.get("https://system-one.dev/v1/models", headers=headers, timeout=8)
        response.raise_for_status()
        catalog = response.json()["models"]
        selected = next((m for m in catalog if m["id"] == self.model), None)
        if not selected or "choice" not in selected.get("capabilities", {}).get("questions", []):
            raise ValueError("Configured choice model unavailable")
        state = {
            "hard_gate_status": result.status,
            "missing_conditions": [c.name for c in result.conditions if c.status == "unknown"],
        }
        response = await client.post(
            "https://system-one.dev/v1/systemone",
            headers=headers,
            json={
                "model": selected["id"],
                "state": state,
                "questions": {
                    "route": {
                        "type": "choice",
                        "instructions": "Choose the safest next allowed investigation step",
                        "criteria": CHOICES,
                    }
                },
            },
            timeout=8,
        )
        response.raise_for_status()
        choice = response.json()["answers"]["route"]["choice"]
        if choice not in CHOICES:
            raise ValueError("Unknown choice")
        return choice
