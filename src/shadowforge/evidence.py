"""Append-only evidence storage."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceRecord:
    timestamp: str
    tool: str
    target: str
    status: str
    data: dict[str, Any]


class EvidenceStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def append(self, *, tool: str, target: str, status: str, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = EvidenceRecord(
            timestamp=datetime.now(UTC).isoformat(),
            tool=tool,
            target=target,
            status=status,
            data=data,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
