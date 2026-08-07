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

    def verify(self) -> int:
        """Verify every record hash and link; return the number of valid records."""

        if not self.path.exists() or self.path.stat().st_size == 0:
            return 0
        expected_previous: str | None = None
        lines = self.path.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines, start=1):
            try:
                record = json.loads(line)
                stored_hash = record.pop("record_hash")
            except (KeyError, TypeError, ValueError) as exc:
                raise EvidenceError(f"evidence record {index} is malformed") from exc
            if not isinstance(record, dict) or not isinstance(stored_hash, str):
                raise EvidenceError(f"evidence record {index} has an invalid record hash")
            if record.get("previous_hash") != expected_previous:
                raise EvidenceError(f"evidence record {index} has a broken previous-hash link")
            calculated_hash = self._hash_payload(record)
            if stored_hash != calculated_hash:
                raise EvidenceError(f"evidence record {index} hash does not match its contents")
            expected_previous = stored_hash
        return len(lines)

    def _previous_hash(self) -> str | None:
        count = self.verify()
        if count == 0:
            return None
        last_line = self.path.read_text(encoding="utf-8").splitlines()[-1]
        previous = json.loads(last_line)
        return str(previous["record_hash"])

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
