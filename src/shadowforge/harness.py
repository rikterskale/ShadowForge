"""Scope-enforced execution harness."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from shadowforge import __version__
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
        execution_id = str(uuid4())
        started = perf_counter()
        result = tool.run(target, arguments)
        duration_ms = max(0, round((perf_counter() - started) * 1000))
        self.evidence.append(
            execution_id=execution_id,
            scope=self.scope.name,
            tool=tool_name,
            target=target,
            arguments=arguments,
            status=result.status,
            duration_ms=duration_ms,
            shadowforge_version=__version__,
            result=result.data,
        )
        return result
