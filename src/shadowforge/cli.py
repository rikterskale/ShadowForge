"""Command-line interface."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from shadowforge.agent import AgentCoordinator, ProposalError
from shadowforge.evidence import EvidenceError, EvidenceStore
from shadowforge.harness import Harness
from shadowforge.model_router import ModelRouter
from shadowforge.models import ModelError
from shadowforge.scope import EngagementScope, ScopeError
from shadowforge.tools.base import ToolRegistry
from shadowforge.tools.nmap import NmapTool


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shadowforge",
        description="Scope-enforced harness for authorized penetration testing.",
    )
    parser.add_argument("--scope", help="Path to engagement scope JSON (required for active tools)")
    parser.add_argument(
        "--authorized",
        action="store_true",
        help="Confirm that you have written authorization for the supplied scope",
    )
    parser.add_argument("--evidence", default="artifacts/evidence.jsonl")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("models", help="Show local Ollama model availability and fallback routing")

    scan = sub.add_parser("scan", help="Run allowlisted non-destructive service discovery")
    scan.add_argument("target")
    scan.add_argument("--ports", default="1-1024")

    agent = sub.add_parser(
        "agent",
        help="Ask the bounded LLM planner for one validated service-discovery action",
    )
    agent.add_argument("objective", help="What you want to learn from the authorized target")
    agent.add_argument("--target", required=True, help="Exact operator-supplied IP or CIDR target")
    agent.add_argument(
        "--execute",
        action="store_true",
        help="Execute the validated proposal; otherwise print a dry-run proposal only",
    )
    return parser


def _print_model_status(router: ModelRouter) -> int:
    try:
        statuses = router.resolve()
    except ModelError as exc:
        print(f"Model error: {exc}")
        return 2
    print("ShadowForge Model Status")
    for status in statuses:
        marker = "FALLBACK" if status.fallback else "OK"
        suffix = f" -> using {status.active_model}" if status.fallback else ""
        print(f"[{marker}] {status.role:7}: {status.preferred_model}{suffix}")
        if status.fallback_reason:
            print(f"           reason: {status.fallback_reason}")
    mode = "QWEN-ONLY FALLBACK" if any(item.fallback for item in statuses) else "FULL MODEL STACK"
    print(f"Mode: {mode}")
    return 0


def _build_harness(args: argparse.Namespace) -> tuple[EngagementScope, Harness]:
    scope = EngagementScope.from_file(Path(args.scope))
    registry = ToolRegistry()
    registry.register(NmapTool())
    harness = Harness(scope=scope, registry=registry, evidence=EvidenceStore(args.evidence))
    return scope, harness


def _run_agent(args: argparse.Namespace) -> int:
    if not args.scope:
        print("Refusing to run: agent mode requires --scope with an authorized scope file.")
        return 2
    if args.execute and not args.authorized:
        print("Refusing to execute: pass --authorized only when you have written authorization.")
        return 2
    try:
        scope, harness = _build_harness(args)
        coordinator = AgentCoordinator(scope=scope, harness=harness, router=ModelRouter())
        run = coordinator.run(
            objective=args.objective,
            target=args.target,
            execute=args.execute,
        )
    except (ScopeError, ProposalError, ValueError, KeyError, EvidenceError, ModelError) as exc:
        print(f"Error: {exc}")
        return 2
    except OSError as exc:
        print(f"File/system error: {exc}")
        return 2

    payload: dict[str, object] = {
        "mode": "execute" if args.execute else "dry-run",
        "proposal": run.proposal.as_dict(),
    }
    if run.result is not None:
        payload["result"] = {"status": run.result.status, **run.result.data}
    if run.critique is not None:
        payload["critique"] = run.critique
    if run.critique_error is not None:
        payload["critique_error"] = run.critique_error
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if run.result is None or run.result.status == "ok" else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "models":
        return _print_model_status(ModelRouter())
    if args.command == "agent":
        return _run_agent(args)
    if not args.scope:
        print("Refusing to run: active tools require --scope with an authorized scope file.")
        return 2
    if not args.authorized:
        print("Refusing to run: pass --authorized only when you have written authorization.")
        return 2
    try:
        _scope, harness = _build_harness(args)
        result = harness.execute(
            tool_name="nmap_service_scan",
            target=args.target,
            arguments={"ports": args.ports},
        )
    except (ScopeError, ValueError, KeyError, EvidenceError) as exc:
        print(f"Error: {exc}")
        return 2
    except OSError as exc:
        print(f"File/system error: {exc}")
        return 2
    print(json.dumps({"status": result.status, **result.data}, indent=2, sort_keys=True))
    return 0 if result.status == "ok" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
