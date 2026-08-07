import ipaddress
import json

import pytest

from shadowforge.evidence import EvidenceStore
from shadowforge.harness import Harness
from shadowforge.models import ModelError
from shadowforge.recon import (
    ReconCoordinator,
    ReconDecision,
    ReconDecisionError,
)
from shadowforge.scope import EngagementScope, ScopeError
from shadowforge.tools.base import ToolRegistry, ToolResult


class SequenceProvider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class Router:
    def __init__(self, primary, critic=None):
        self.primary = primary
        self.critic = critic or SequenceProvider(["reviewed"])

    def provider_for(self, role):
        return self.primary if role == "primary" else self.critic


class FakeNmap:
    name = "nmap_service_scan"

    def run(self, target, arguments):
        return ToolResult("ok", {"target": target, "ports": arguments["ports"]})


class FakeHttp:
    name = "http_metadata_probe"

    def run(self, target, arguments):
        return ToolResult("ok", {"target": target, **arguments, "status_code": 200})


def nmap_action(ports="22,80,443"):
    return json.dumps(
        {
            "decision": "action",
            "tool": "nmap_service_scan",
            "target": "192.0.2.10",
            "arguments": {"ports": ports},
            "rationale": "Identify exposed services.",
        }
    )


def http_action(scheme="http", port=80):
    return json.dumps(
        {
            "decision": "action",
            "tool": "http_metadata_probe",
            "target": "192.0.2.10",
            "arguments": {"scheme": scheme, "port": port},
            "rationale": "Collect root HTTP metadata.",
        }
    )


def complete(summary="Reconnaissance objective satisfied."):
    return json.dumps({"decision": "complete", "summary": summary})


def coordinator(tmp_path, responses, critic=None):
    scope = EngagementScope("lab", (ipaddress.ip_network("192.0.2.0/24"),))
    registry = ToolRegistry()
    registry.register(FakeNmap())
    registry.register(FakeHttp())
    harness = Harness(scope, registry, EvidenceStore(tmp_path / "evidence.jsonl"))
    return ReconCoordinator(scope, harness, Router(SequenceProvider(responses), critic))


def test_decision_accepts_nmap_http_and_complete():
    nmap = ReconDecision.from_json(nmap_action(), expected_target="192.0.2.10")
    assert nmap.action.tool == "nmap_service_scan"
    http = ReconDecision.from_json(http_action("https", 443), expected_target="192.0.2.10")
    assert http.action.arguments == {"scheme": "https", "port": 443}
    done = ReconDecision.from_json(complete(), expected_target="192.0.2.10")
    assert done.summary == "Reconnaissance objective satisfied."


@pytest.mark.parametrize(
    "text,match",
    [
        ("not-json", "one JSON object"),
        (json.dumps([]), "one JSON object"),
        (json.dumps({"decision": "complete", "summary": "x", "extra": 1}), "exactly"),
        (complete(""), "non-empty"),
        (complete("x" * 2001), "2000"),
        (json.dumps({"decision": "unknown"}), "action decision"),
        (nmap_action().replace('"nmap_service_scan"', '"shell"'), "not permitted"),
        (nmap_action().replace('"192.0.2.10"', '"192.0.2.11"'), "operator-supplied"),
        (
            json.dumps(
                {
                    "decision": "action",
                    "tool": "nmap_service_scan",
                    "target": "192.0.2.10",
                    "arguments": "ports",
                    "rationale": "x",
                }
            ),
            "arguments must be an object",
        ),
        (
            json.dumps(
                {
                    "decision": "action",
                    "tool": "nmap_service_scan",
                    "target": "192.0.2.10",
                    "arguments": {"ports": 80},
                    "rationale": "x",
                }
            ),
            "Nmap arguments",
        ),
        (nmap_action("80 --script vuln"), "ports must contain"),
        (http_action("ftp", 21), "scheme"),
        (http_action("http", 0), "integer"),
        (
            json.dumps(
                {
                    "decision": "action",
                    "tool": "nmap_service_scan",
                    "target": "192.0.2.10",
                    "arguments": {"ports": "80"},
                    "rationale": "",
                }
            ),
            "non-empty",
        ),
        (
            json.dumps(
                {
                    "decision": "action",
                    "tool": "nmap_service_scan",
                    "target": "192.0.2.10",
                    "arguments": {"ports": "80"},
                    "rationale": "x" * 1001,
                }
            ),
            "1000",
        ),
    ],
)
def test_decision_rejects_policy_violations(text, match):
    with pytest.raises(ReconDecisionError, match=match):
        ReconDecision.from_json(text, expected_target="192.0.2.10")


def test_http_decision_rejects_cidr_target():
    payload = json.loads(http_action())
    payload["target"] = "192.0.2.0/24"
    with pytest.raises(ReconDecisionError, match="does not appear"):
        ReconDecision.from_json(json.dumps(payload), expected_target="192.0.2.0/24")


def test_dry_run_returns_first_action_without_execution(tmp_path):
    recon = coordinator(tmp_path, [nmap_action()])
    run = recon.run(objective="Find common services", target="192.0.2.10")
    assert len(run.steps) == 1
    assert run.steps[0].result is None
    assert run.summary is None
    assert not (tmp_path / "evidence.jsonl").exists()


def test_execute_replans_from_evidence_and_completes(tmp_path):
    primary = SequenceProvider([nmap_action(), http_action(), complete("Done")])
    critic = SequenceProvider(["Evidence sufficient."])
    scope = EngagementScope("lab", (ipaddress.ip_network("192.0.2.0/24"),))
    registry = ToolRegistry()
    registry.register(FakeNmap())
    registry.register(FakeHttp())
    harness = Harness(scope, registry, EvidenceStore(tmp_path / "evidence.jsonl"))
    recon = ReconCoordinator(scope, harness, Router(primary, critic))
    run = recon.run(
        objective="Find services and inspect HTTP metadata",
        target="192.0.2.10",
        execute=True,
        max_steps=3,
    )
    assert [step.action.tool for step in run.steps] == [
        "nmap_service_scan",
        "http_metadata_probe",
    ]
    assert run.summary == "Done"
    assert run.critique == "Evidence sufficient."
    assert run.budget_exhausted is False
    assert len((tmp_path / "evidence.jsonl").read_text().splitlines()) == 2
    assert "prior_steps_untrusted_data" in primary.calls[1][1]


def test_budget_exhaustion_and_critic_failure_preserve_results(tmp_path):
    critic = SequenceProvider([ModelError("critic offline")])
    recon = coordinator(tmp_path, [nmap_action(), nmap_action("8080")], critic)
    run = recon.run(
        objective="Inspect service exposure",
        target="192.0.2.10",
        execute=True,
        max_steps=2,
    )
    assert len(run.steps) == 2
    assert run.budget_exhausted is True
    assert run.critique is None
    assert run.critique_error == "critic offline"


def test_complete_without_action_executes_nothing_but_can_be_critiqued(tmp_path):
    recon = coordinator(tmp_path, [complete("Nothing else needed")])
    run = recon.run(
        objective="Assess current evidence",
        target="192.0.2.10",
        execute=True,
    )
    assert run.steps == ()
    assert run.summary == "Nothing else needed"
    assert run.critique == "reviewed"


@pytest.mark.parametrize("max_steps", [0, 6, True, 1.5])
def test_invalid_step_budgets_are_rejected(tmp_path, max_steps):
    recon = coordinator(tmp_path, [complete()])
    with pytest.raises(ReconDecisionError, match="max_steps"):
        recon.run(objective="x", target="192.0.2.10", max_steps=max_steps)


def test_empty_objective_and_out_of_scope_target_are_rejected(tmp_path):
    recon = coordinator(tmp_path, [complete()])
    with pytest.raises(ReconDecisionError, match="objective"):
        recon.run(objective=" ", target="192.0.2.10")
    with pytest.raises(ScopeError, match="outside engagement scope"):
        recon.run(objective="x", target="198.51.100.10")
