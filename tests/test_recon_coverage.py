import ipaddress
import json

from shadowforge.evidence import EvidenceStore
from shadowforge.harness import Harness
from shadowforge.recon import ReconAction, ReconCoordinator, ReconDecision
from shadowforge.scope import EngagementScope
from shadowforge.tools.base import ToolRegistry


class Provider:
    def __init__(self, response):
        self.response = response

    def complete(self, system_prompt, user_prompt):
        return self.response


class Router:
    def __init__(self, response):
        self.provider = Provider(response)

    def provider_for(self, role):
        return self.provider


def test_recon_decision_as_dict():
    decision = ReconDecision(
        decision="action",
        action=ReconAction(
            "nmap_service_scan",
            "192.0.2.10",
            {"ports": "80"},
            "Inspect HTTP exposure.",
        ),
    )
    assert decision.as_dict()["action"]["tool"] == "nmap_service_scan"


def test_dry_run_can_complete_without_active_step(tmp_path):
    scope = EngagementScope("lab", (ipaddress.ip_network("192.0.2.0/24"),))
    harness = Harness(scope, ToolRegistry(), EvidenceStore(tmp_path / "evidence.jsonl"))
    response = json.dumps({"decision": "complete", "summary": "No action required."})
    coordinator = ReconCoordinator(scope, harness, Router(response))
    run = coordinator.run(objective="Assess whether more recon is needed", target="192.0.2.10")
    assert run.steps == ()
    assert run.summary == "No action required."
    assert run.budget_exhausted is False
    assert not (tmp_path / "evidence.jsonl").exists()
