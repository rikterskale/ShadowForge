"""Scope-enforced execution harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shadowforge.evidence import EvidenceStore
from shadowforge.scope import EngagementScope
from shadowforge.tools.base import ToolRegistry, ToolResult


@dataclass
class Harness:
    scope: EngagementScope
    registry: ToolRegistry
    evidence: EvidenceStore

    def execute(self, *, tool_name: str, target: str, arguments: dict[str, Any]) -> ToolResult:
        self.scope.require(target)
        tool = self.registry.get(tool_name)
        result = tool.run(target, arguments)
        self.evidence.append(
            tool=tool_name,
            target=target,
            status=result.status,
            data=result.data,
        )
        return result
