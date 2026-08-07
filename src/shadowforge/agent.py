"""Structured, policy-constrained LLM planning for Phase 2."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from shadowforge.harness import Harness
from shadowforge.model_router import ModelRouter
from shadowforge.models import ModelError
from shadowforge.scope import EngagementScope
from shadowforge.tools.base import ToolResult
from shadowforge.tools.nmap import validate_ports

ALLOWED_AGENT_TOOL = "nmap_service_scan"
PROPOSAL_KEYS = frozenset({"tool", "target", "arguments", "rationale"})


class ProposalError(ValueError):
    """Raised when a model proposal violates the Phase 2 action schema or policy."""


@dataclass(frozen=True)
class ActionProposal:
    tool: str
    target: str
    arguments: dict[str, str]
    rationale: str

    @classmethod
    def from_json(cls, text: str, *, expected_target: str) -> ActionProposal:
        try:
            payload = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise ProposalError("planner response must be one JSON object") from exc
        if not isinstance(payload, dict) or set(payload) != PROPOSAL_KEYS:
            raise ProposalError(
                "proposal must contain exactly: tool, target, arguments, rationale"
            )
        tool = payload["tool"]
        target = payload["target"]
        arguments = payload["arguments"]
        rationale = payload["rationale"]
        if tool != ALLOWED_AGENT_TOOL:
            raise ProposalError(f"tool is not permitted for Phase 2 agent mode: {tool!r}")
        if not isinstance(target, str) or target != expected_target:
            raise ProposalError("proposal target must exactly match the operator-supplied target")
        if not isinstance(arguments, dict) or set(arguments) != {"ports"}:
            raise ProposalError("proposal arguments must contain exactly one 'ports' field")
        ports = arguments["ports"]
        if not isinstance(ports, str):
            raise ProposalError("proposal ports must be a string")
        try:
            validate_ports(ports)
        except ValueError as exc:
            raise ProposalError(str(exc)) from exc
        if not isinstance(rationale, str) or not rationale.strip():
            raise ProposalError("proposal rationale must be a non-empty string")
        if len(rationale) > 1000:
            raise ProposalError("proposal rationale must be 1000 characters or fewer")
        return cls(tool=tool, target=target, arguments={"ports": ports}, rationale=rationale.strip())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentRun:
    proposal: ActionProposal
    result: ToolResult | None
    critique: str | None
    critique_error: str | None = None


@dataclass
class AgentCoordinator:
    """Plan one bounded action, optionally execute it, then request an advisory critique."""

    scope: EngagementScope
    harness: Harness
    router: ModelRouter

    @staticmethod
    def _planner_system_prompt() -> str:
        return (
            "You are ShadowForge's bounded planning component for an authorized assessment. "
            "Return exactly one JSON object and no markdown. The only allowed tool is "
            "nmap_service_scan. Never propose shell commands, scripts, credentials, exploitation, "
            "persistence, evasion, relay, coercion, or a different target. The JSON schema is: "
            '{"tool":"nmap_service_scan","target":"<exact target>",'
            '"arguments":{"ports":"<ports or ascending ranges>"},"rationale":"<brief reason>"}.'
        )

    def plan(self, *, objective: str, target: str) -> ActionProposal:
        if not isinstance(objective, str) or not objective.strip():
            raise ProposalError("objective must be a non-empty string")
        self.scope.require(target)
        provider = self.router.provider_for("primary")
        user_prompt = (
            f"Operator target: {target}\n"
            f"Objective: {objective.strip()}\n"
            "Choose only the TCP ports needed for a non-destructive service-discovery scan."
        )
        response = provider.complete(self._planner_system_prompt(), user_prompt)
        proposal = ActionProposal.from_json(response, expected_target=target)
        self.scope.require(proposal.target)
        return proposal

    def critique(
        self,
        *,
        objective: str,
        proposal: ActionProposal,
        result: ToolResult,
    ) -> str:
        provider = self.router.provider_for("critic")
        system_prompt = (
            "You are ShadowForge's advisory critic. Review the completed non-destructive scan. "
            "Do not propose commands or additional tool execution. Briefly assess whether the "
            "result addressed the stated objective and identify evidence or interpretation gaps."
        )
        user_prompt = json.dumps(
            {
                "objective": objective,
                "proposal": proposal.as_dict(),
                "result": {"status": result.status, "data": result.data},
            },
            sort_keys=True,
        )
        return provider.complete(system_prompt, user_prompt)

    def run(self, *, objective: str, target: str, execute: bool = False) -> AgentRun:
        proposal = self.plan(objective=objective, target=target)
        if not execute:
            return AgentRun(proposal=proposal, result=None, critique=None)
        result = self.harness.execute(
            tool_name=proposal.tool,
            target=proposal.target,
            arguments=proposal.arguments,
        )
        try:
            critique = self.critique(objective=objective, proposal=proposal, result=result)
        except ModelError as exc:
            return AgentRun(
                proposal=proposal,
                result=result,
                critique=None,
                critique_error=str(exc),
            )
        return AgentRun(proposal=proposal, result=result, critique=critique)
