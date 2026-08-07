"""Persistent, validated engagement state for bounded reconnaissance sessions."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

_STATE_VERSION = 1
_SESSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_MAX_OBSERVATIONS = 100


class StateError(ValueError):
    """Raised when persistent state is invalid, unsafe, or inconsistent."""


@dataclass(frozen=True)
class Observation:
    step: int
    tool: str
    target: str
    status: str
    data: dict[str, Any]


@dataclass
class EngagementState:
    session_id: str
    target: str
    objective: str
    observations: list[Observation] = field(default_factory=list)
    summary: str | None = None
    version: int = _STATE_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "session_id": self.session_id,
            "target": self.target,
            "objective": self.objective,
            "observations": [asdict(item) for item in self.observations],
            "summary": self.summary,
        }

    def planner_context(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "target": self.target,
            "objective": self.objective,
            "observations_untrusted_data": [asdict(item) for item in self.observations],
            "prior_summary_untrusted_data": self.summary,
        }


class EngagementStateStore:
    """Store per-session JSON state using atomic file replacement."""

    def __init__(self, root: str | Path = "artifacts/state") -> None:
        self.root = Path(root)

    @staticmethod
    def validate_session_id(session_id: str) -> str:
        if not isinstance(session_id, str) or not _SESSION_RE.fullmatch(session_id):
            raise StateError(
                "session must be 1-64 characters using letters, numbers, dot, underscore, or hyphen"
            )
        return session_id

    def path_for(self, session_id: str) -> Path:
        valid = self.validate_session_id(session_id)
        return self.root / f"{valid}.json"

    def load_or_create(self, *, session_id: str, target: str, objective: str) -> EngagementState:
        path = self.path_for(session_id)
        if not path.exists():
            return EngagementState(session_id=session_id, target=target, objective=objective.strip())
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateError(f"could not read session state: {exc}") from exc
        state = self._parse(payload)
        if state.target != target:
            raise StateError(
                f"session {session_id!r} is bound to target {state.target!r}, not {target!r}"
            )
        if state.objective != objective.strip():
            raise StateError("session objective does not match the stored objective")
        return state

    def save(self, state: EngagementState) -> None:
        path = self.path_for(state.session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        text = json.dumps(state.as_dict(), indent=2, sort_keys=True) + "\n"
        try:
            temp.write_text(text, encoding="utf-8")
            os.replace(temp, path)
        except OSError as exc:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass
            raise StateError(f"could not write session state: {exc}") from exc

    def append_result(
        self,
        state: EngagementState,
        *,
        step: int,
        tool: str,
        target: str,
        status: str,
        data: dict[str, Any],
    ) -> None:
        if len(state.observations) >= _MAX_OBSERVATIONS:
            raise StateError("session observation limit reached")
        safe_data = self._sanitize(tool, data)
        state.observations.append(Observation(step, tool, target, status, safe_data))
        self.save(state)

    @staticmethod
    def _sanitize(tool: str, data: dict[str, Any]) -> dict[str, Any]:
        if tool == "nmap_service_scan":
            services = data.get("services", [])
            if not isinstance(services, list):
                return {"error": "unexpected Nmap result shape"}
            return {"services": services[:256]}
        if tool == "http_metadata_probe":
            allowed = {"scheme", "port", "status_code", "reason", "headers", "error"}
            return {key: value for key, value in data.items() if key in allowed}
        raise StateError(f"tool is not permitted in persistent state: {tool!r}")

    @classmethod
    def _parse(cls, payload: Any) -> EngagementState:
        if not isinstance(payload, dict) or set(payload) != {
            "version",
            "session_id",
            "target",
            "objective",
            "observations",
            "summary",
        }:
            raise StateError("session state has an invalid schema")
        if payload["version"] != _STATE_VERSION:
            raise StateError(f"unsupported session state version: {payload['version']!r}")
        session_id = cls.validate_session_id(payload["session_id"])
        target = payload["target"]
        objective = payload["objective"]
        summary = payload["summary"]
        observations = payload["observations"]
        if not isinstance(target, str) or not target:
            raise StateError("session target must be a non-empty string")
        if not isinstance(objective, str) or not objective:
            raise StateError("session objective must be a non-empty string")
        if summary is not None and not isinstance(summary, str):
            raise StateError("session summary must be a string or null")
        if not isinstance(observations, list) or len(observations) > _MAX_OBSERVATIONS:
            raise StateError("session observations must be a bounded list")
        parsed: list[Observation] = []
        for item in observations:
            if not isinstance(item, dict) or set(item) != {"step", "tool", "target", "status", "data"}:
                raise StateError("session observation has an invalid schema")
            if (
                not isinstance(item["step"], int)
                or isinstance(item["step"], bool)
                or item["step"] < 1
                or not isinstance(item["tool"], str)
                or not isinstance(item["target"], str)
                or not isinstance(item["status"], str)
                or not isinstance(item["data"], dict)
            ):
                raise StateError("session observation has invalid field types")
            parsed.append(Observation(**item))
        return EngagementState(session_id, target, objective, parsed, summary, _STATE_VERSION)
