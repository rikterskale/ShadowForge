"""Engagement-scope parsing and enforcement."""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from pathlib import Path


class ScopeError(ValueError):
    """Raised when a target is invalid or outside the authorized scope."""


@dataclass(frozen=True)
class EngagementScope:
    name: str
    networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]

    @classmethod
    def from_file(cls, path: str | Path) -> "EngagementScope":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("name"), str):
            raise ScopeError("scope file must contain a string 'name'")
        raw_targets = data.get("targets")
        if not isinstance(raw_targets, list) or not raw_targets:
            raise ScopeError("scope file must contain a non-empty 'targets' list")
        try:
            networks = tuple(ipaddress.ip_network(item, strict=False) for item in raw_targets)
        except (TypeError, ValueError) as exc:
            raise ScopeError(f"invalid target in scope file: {exc}") from exc
        return cls(name=data["name"], networks=networks)

    def contains(self, target: str) -> bool:
        try:
            candidate = ipaddress.ip_network(target, strict=False)
        except ValueError as exc:
            raise ScopeError("Phase 1 accepts only IP addresses and CIDR ranges") from exc
        return any(candidate.subnet_of(network) for network in self.networks)

    def require(self, target: str) -> None:
        if not self.contains(target):
            raise ScopeError(f"target {target!r} is outside engagement scope {self.name!r}")
