"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shadowforge.evidence import EvidenceStore
from shadowforge.harness import Harness
from shadowforge.scope import EngagementScope, ScopeError
from shadowforge.tools.base import ToolRegistry
from shadowforge.tools.nmap import NmapTool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shadowforge",
        description="Scope-enforced harness for authorized penetration testing.",
    )
    parser.add_argument("--scope", required=True, help="Path to engagement scope JSON")
    parser.add_argument(
        "--authorized",
        action="store_true",
        help="Confirm that you have written authorization for the supplied scope",
    )
    parser.add_argument("--evidence", default="artifacts/evidence.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Run allowlisted non-destructive service discovery")
    scan.add_argument("target")
    scan.add_argument("--ports", default="1-1024")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.authorized:
        print("Refusing to run: pass --authorized only when you have written authorization.")
        return 2
    try:
        scope = EngagementScope.from_file(Path(args.scope))
        registry = ToolRegistry()
        registry.register(NmapTool())
        harness = Harness(scope=scope, registry=registry, evidence=EvidenceStore(args.evidence))
        result = harness.execute(
            tool_name="nmap_service_scan",
            target=args.target,
            arguments={"ports": args.ports},
        )
    except (ScopeError, ValueError, KeyError) as exc:
        print(f"Error: {exc}")
        return 2
    print(json.dumps({"status": result.status, **result.data}, indent=2, sort_keys=True))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
