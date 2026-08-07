"""Tool contracts and registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolResult:
    status: str
    data: dict[str, Any]


class Tool(Protocol):
    name: str

    def run(self, target: str, arguments: dict[str, Any]) -> ToolResult: ...


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"tool is not allowlisted: {name}") from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
