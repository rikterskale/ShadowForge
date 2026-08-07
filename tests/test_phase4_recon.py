import ipaddress
import json

from shadowforge.evidence import EvidenceStore
from shadowforge.harness import Harness
from shadowforge.recon import ReconCoordinator
from shadowforge.scope import EngagementScope
from shadowforge.state import EngagementStateStore
from shadowforge.tools.base import ToolRegistry, ToolResult


class Provider:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.responses.pop(0)


class Router:
    def __init__(self, primary, critic=None):
        self.primary = primary
        self.critic = critic or Provider(["reviewed"])

    def provider_for(self, role):
        return self.primary if role == "primary" else self.critic


class FakeNmap:
    name = "nmap_service_scan"

    def run(self, target, arguments):
        return ToolResult("ok", {"services": [{"port": 80, "service": "http"}]})


def action():
    return json.dumps(
        {
            "decision": "action",
            "tool": "nmap_service_scan",
            "target": "192.0.2.10",
            "arguments": {"ports": "80"},
            "rationale": "Inspect HTTP exposure.",
        }
    )


def complete():
    return json.dumps({"decision": "complete", "summary": "Recon complete."})


def build(tmp_path, primary, critic=None):
    scope = EngagementScope("lab", (ipaddress.ip_network("192.0.2.0/24"),))
    registry = ToolRegistry()
    registry.register(FakeNmap())
    harness = Harness(scope, registry, EvidenceStore(tmp_path / "evidence.jsonl"))
    store = EngagementStateStore(tmp_path / "state")
    return ReconCoordinator(
        scope,
        harness,
        Router(primary, critic),
        state_store=store,
        session_id="case-1",
    ), store


def test_persistent_session_records_and_resumes(tmp_path):
    first_provider = Provider([action()])
    coordinator, store = build(tmp_path, first_provider)
    first = coordinator.run(
        objective="Inspect services",
        target="192.0.2.10",
        execute=True,
        max_steps=1,
    )
    assert first.session_id == "case-1"
    assert first.prior_observation_count == 0
    stored = store.load_or_create(
        session_id="case-1",
        target="192.0.2.10",
        objective="Inspect services",
    )
    assert len(stored.observations) == 1

    second_provider = Provider([complete()])
    second_critic = Provider(["continuous evidence reviewed"])
    resumed, _ = build(tmp_path, second_provider, second_critic)
    second = resumed.run(
        objective="Inspect services",
        target="192.0.2.10",
        execute=True,
        max_steps=2,
    )
    assert second.prior_observation_count == 1
    assert second.summary == "Recon complete."
    assert "persistent_session_untrusted_data" in second_provider.calls[0][1]
    assert "observations_untrusted_data" in second_provider.calls[0][1]
    assert "persistent_session_untrusted_data" in second_critic.calls[0][1]
    reloaded = store.load_or_create(
        session_id="case-1",
        target="192.0.2.10",
        objective="Inspect services",
    )
    assert reloaded.summary == "Recon complete."


def test_persistent_dry_run_does_not_create_state_file(tmp_path):
    provider = Provider([action()])
    coordinator, store = build(tmp_path, provider)
    run = coordinator.run(objective="Inspect services", target="192.0.2.10")
    assert run.session_id == "case-1"
    assert run.steps[0].result is None
    assert not store.path_for("case-1").exists()


def test_recon_without_session_keeps_previous_behavior(tmp_path):
    scope = EngagementScope("lab", (ipaddress.ip_network("192.0.2.0/24"),))
    registry = ToolRegistry()
    registry.register(FakeNmap())
    harness = Harness(scope, registry, EvidenceStore(tmp_path / "evidence.jsonl"))
    provider = Provider([action()])
    coordinator = ReconCoordinator(scope, harness, Router(provider))
    run = coordinator.run(objective="Inspect services", target="192.0.2.10")
    assert run.session_id is None
    assert run.prior_observation_count == 0
    assert "\"persistent_session_untrusted_data\": null" in provider.calls[0][1]
