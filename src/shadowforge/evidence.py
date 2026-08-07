"""Append-only, tamper-evident evidence storage."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EvidenceError(RuntimeError):
    """Raised when the evidence chain cannot be read or extended safely."""


@dataclass(frozen=True)
class EvidenceRecord:
    execution_id: str
    timestamp: str
    scope: str
    tool: str
    target: str
    arguments: dict[str, Any]
    status: str
    duration_ms: int
    shadowforge_version: str
    result: dict[str, Any]
    previous_hash: str | None
    record_hash: str


class EvidenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()

    def _previous_hash(self) -> str | None:
        if not self.path.exists() or self.path.stat().st_size == 0:
            return None
        try:
            last_line = self.path.read_text(encoding="utf-8").splitlines()[-1]
            previous = json.loads(last_line)
            record_hash = previous["record_hash"]
        except (IndexError, KeyError, TypeError, ValueError) as exc:
            raise EvidenceError("existing evidence file has an invalid final record") from exc
        if not isinstance(record_hash, str):
            raise EvidenceError("existing evidence record hash is invalid")
        return record_hash

    def append(
        self,
        *,
        execution_id: str,
        scope: str,
        tool: str,
        target: str,
        arguments: dict[str, Any],
        status: str,
        duration_ms: int,
        shadowforge_version: str,
        result: dict[str, Any],
    ) -> EvidenceRecord:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        previous_hash = self._previous_hash()
        unsigned = {
            "execution_id": execution_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "scope": scope,
            "tool": tool,
            "target": target,
            "arguments": arguments,
            "status": status,
            "duration_ms": duration_ms,
            "shadowforge_version": shadowforge_version,
            "result": result,
            "previous_hash": previous_hash,
        }
        record = EvidenceRecord(**unsigned, record_hash=self._hash_payload(unsigned))
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
        return record
