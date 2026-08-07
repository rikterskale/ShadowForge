import ipaddress
import json

import pytest

from shadowforge.agent import ActionProposal, AgentCoordinator, ProposalError
from shadowforge.evidence import EvidenceStore
from shadowforge.harness import Harness
from shadowforge.scope import EngagementScope, ScopeError
from shadowforge.tools.base import ToolRegistry, ToolResult


class Provider:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.response


class Router:
    def __init__(self, primary, critic=None):
        self.primary = primary
        self.critic = critic or Provider("reviewed")

    def provider_for(self, role):
        return self.primary if role == "primary" else self.critic


class FakeTool:
    name = "nmap_service_scan"

    def run(self, target, arguments):
        return ToolResult("ok", {"target": target, "ports": arguments["ports"]})


def coordinator(tmp_path, response):
    scope = EngagementScope("lab", (ipaddress.ip_network("192.0.2.0/24"),))
    registry = ToolRegistry()
    registry.register(FakeTool())
    harness = Harness(scope, registry, EvidenceStore(tmp_path / "evidence.jsonl"))
    return AgentCoordinator(scope, harness, Router(Provider(response)))


def proposal_json(**updates):
    payload = {
        "tool": "nmap_service_scan",
        "target": "192.0.2.10",
        "arguments": {"ports": "22,80,443"},
        "rationale": "Identify common exposed services.",
    }
    payload.update(updates)
    return json.dumps(payload)


def test_proposal_accepts_exact_bounded_schema():
    proposal = ActionProposal.from_json(proposal_json(), expected_target="192.0.2.10")
    assert proposal.tool == "nmap_service_scan"
    assert proposal.arguments == {"ports": "22,80,443"}
    assert proposal.as_dict()["target"] == "192.0.2.10"


@pytest.mark.parametrize(
    "text,match",
    [
        ("not-json", "one JSON object"),
        (json.dumps([]), "contain exactly"),
        (proposal_json(extra="x"), "contain exactly"),
        (proposal_json(tool="shell"), "not permitted"),
        (proposal_json(target="192.0.2.11"), "operator-supplied target"),
        (proposal_json(arguments={"ports": "80", "script": "x"}), "exactly one 'ports'"),
        (proposal_json(arguments={"ports": 80}), "ports must be a string"),
        (proposal_json(arguments={"ports": "80 --script vuln"}), "ports must contain"),
        (proposal_json(rationale=""), "non-empty string"),
        (proposal_json(rationale="x" * 1001), "1000 characters"),
    ],
)
def test_proposal_rejects_policy_violations(text, match):
    with pytest.raises(ProposalError, match=match):
        ActionProposal.from_json(text, expected_target="192.0.2.10")


def test_agent_dry_run_plans_without_tool_execution(tmp_path):
    agent = coordinator(tmp_path, proposal_json())
    run = agent.run(objective="Find web and remote administration services", target="192.0.2.10")
    assert run.result is None
    assert run.critique is None
    assert not (tmp_path / "evidence.jsonl").exists()


def test_agent_execute_uses_harness_and_critic(tmp_path):
    agent = coordinator(tmp_path, proposal_json())
    run = agent.run(
        objective="Find common services",
        target="192.0.2.10",
        execute=True,
    )
    assert run.result.status == "ok"
    assert run.critique == "reviewed"
    assert (tmp_path / "evidence.jsonl").exists()


def test_agent_rejects_empty_objective_and_out_of_scope_target(tmp_path):
    agent = coordinator(tmp_path, proposal_json())
    with pytest.raises(ProposalError, match="objective"):
        agent.plan(objective=" ", target="192.0.2.10")
    with pytest.raises(ScopeError, match="outside engagement scope"):
        agent.plan(objective="scan", target="198.51.100.10")
