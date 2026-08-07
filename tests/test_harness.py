import ipaddress
import json

import pytest

from shadowforge.evidence import EvidenceStore
from shadowforge.harness import Harness
from shadowforge.scope import EngagementScope, ScopeError
from shadowforge.tools.base import ToolRegistry, ToolResult


class FakeTool:
    name = "fake"

    def run(self, target, arguments):
        return ToolResult(status="ok", data={"target": target, "arguments": arguments})


def test_harness_enforces_scope_and_writes_evidence(tmp_path):
    registry = ToolRegistry()
    registry.register(FakeTool())
    evidence = tmp_path / "evidence.jsonl"
    harness = Harness(
        scope=EngagementScope("lab", (ipaddress.ip_network("10.0.0.0/24"),)),
        registry=registry,
        evidence=EvidenceStore(evidence),
    )
    result = harness.execute(tool_name="fake", target="10.0.0.10", arguments={"x": 1})
    assert result.status == "ok"
    record = json.loads(evidence.read_text())
    assert record["scope"] == "lab"
    assert record["tool"] == "fake"
    assert record["target"] == "10.0.0.10"
    assert record["arguments"] == {"x": 1}
    assert record["duration_ms"] >= 0
    assert record["shadowforge_version"] == "0.1.0"
    assert record["execution_id"]
    assert len(record["record_hash"]) == 64
    with pytest.raises(ScopeError):
        harness.execute(tool_name="fake", target="10.0.1.10", arguments={})
    with pytest.raises(KeyError):
        harness.execute(tool_name="missing", target="10.0.0.10", arguments={})


def test_registry_duplicate_and_names():
    registry = ToolRegistry()
    registry.register(FakeTool())
    assert registry.names() == ("fake",)
    with pytest.raises(ValueError):
        registry.register(FakeTool())
