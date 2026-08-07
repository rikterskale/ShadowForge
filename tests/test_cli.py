import json
from unittest.mock import patch

from shadowforge.agent import ActionProposal, AgentRun, ProposalError
from shadowforge.cli import main
from shadowforge.evidence import EvidenceError
from shadowforge.model_router import ModelStatus
from shadowforge.models import ModelError
from shadowforge.tools.base import ToolResult


def scope_file(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "lab", "targets": ["192.0.2.0/24"]}))
    return path


def test_cli_requires_scope(capsys):
    code = main(["scan", "192.0.2.1"])
    assert code == 2
    assert "active tools require --scope" in capsys.readouterr().out


def test_cli_requires_authorization(tmp_path, capsys):
    code = main(["--scope", str(scope_file(tmp_path)), "scan", "192.0.2.1"])
    assert code == 2
    assert "Refusing" in capsys.readouterr().out


def test_cli_success(tmp_path, capsys):
    with patch("shadowforge.cli.NmapTool.run", return_value=ToolResult("ok", {"services": []})):
        code = main(["--scope", str(scope_file(tmp_path)), "--authorized", "scan", "192.0.2.1"])
    assert code == 0
    assert '"status": "ok"' in capsys.readouterr().out


def test_cli_scope_error(tmp_path, capsys):
    code = main(["--scope", str(scope_file(tmp_path)), "--authorized", "scan", "198.51.100.1"])
    assert code == 2
    assert "outside engagement scope" in capsys.readouterr().out


def test_cli_tool_error(tmp_path):
    with patch("shadowforge.cli.NmapTool.run", return_value=ToolResult("error", {"error": "x"})):
        code = main(["--scope", str(scope_file(tmp_path)), "--authorized", "scan", "192.0.2.1"])
    assert code == 1


def test_cli_reports_missing_scope_file(capsys):
    code = main(["--scope", "missing.json", "--authorized", "scan", "192.0.2.1"])
    assert code == 2
    assert "File/system error" in capsys.readouterr().out


def test_cli_reports_evidence_errors(tmp_path, capsys):
    with patch("shadowforge.cli.Harness.execute", side_effect=EvidenceError("bad chain")):
        code = main(["--scope", str(scope_file(tmp_path)), "--authorized", "scan", "192.0.2.1"])
    assert code == 2
    assert "bad chain" in capsys.readouterr().out


def test_cli_models_full_stack(capsys):
    statuses = (
        ModelStatus("primary", "qwen3.5:27b", "qwen3.5:27b", False, None),
        ModelStatus("critic", "gemma4:31b", "gemma4:31b", False, None),
        ModelStatus("coding", "devstral-small-2:24b", "devstral-small-2:24b", False, None),
    )
    with patch("shadowforge.cli.ModelRouter.resolve", return_value=statuses):
        code = main(["models"])
    output = capsys.readouterr().out
    assert code == 0
    assert "FULL MODEL STACK" in output
    assert "[OK] primary" in output


def test_cli_models_qwen_only_fallback(capsys):
    statuses = (
        ModelStatus("primary", "qwen3.5:27b", "qwen3.5:27b", False, None),
        ModelStatus("critic", "gemma4:31b", "qwen3.5:27b", True, "missing critic"),
        ModelStatus("coding", "devstral-small-2:24b", "qwen3.5:27b", True, "missing coding"),
    )
    with patch("shadowforge.cli.ModelRouter.resolve", return_value=statuses):
        code = main(["models"])
    output = capsys.readouterr().out
    assert code == 0
    assert "QWEN-ONLY FALLBACK" in output
    assert "[FALLBACK] critic" in output
    assert "-> using qwen3.5:27b" in output
    assert "reason: missing critic" in output


def test_cli_models_reports_missing_primary(capsys):
    with patch(
        "shadowforge.cli.ModelRouter.resolve",
        side_effect=ModelError("qwen3.5:27b is not installed"),
    ):
        code = main(["models"])
    assert code == 2
    assert "Model error" in capsys.readouterr().out


def sample_run(*, executed=False, status="ok"):
    proposal = ActionProposal(
        "nmap_service_scan",
        "192.0.2.10",
        {"ports": "22,80,443"},
        "Identify common services.",
    )
    if not executed:
        return AgentRun(proposal, None, None)
    return AgentRun(proposal, ToolResult(status, {"services": []}), "Looks sufficient.")


def test_cli_agent_requires_scope(capsys):
    code = main(["agent", "Find services", "--target", "192.0.2.10"])
    assert code == 2
    assert "agent mode requires --scope" in capsys.readouterr().out


def test_cli_agent_dry_run_does_not_require_authorized(tmp_path, capsys):
    with patch("shadowforge.cli.AgentCoordinator.run", return_value=sample_run()):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "agent",
                "Find services",
                "--target",
                "192.0.2.10",
            ]
        )
    output = capsys.readouterr().out
    assert code == 0
    assert '"mode": "dry-run"' in output
    assert '"proposal"' in output


def test_cli_agent_execute_requires_authorized(tmp_path, capsys):
    code = main(
        [
            "--scope",
            str(scope_file(tmp_path)),
            "agent",
            "Find services",
            "--target",
            "192.0.2.10",
            "--execute",
        ]
    )
    assert code == 2
    assert "Refusing to execute" in capsys.readouterr().out


def test_cli_agent_execute_prints_result_and_critique(tmp_path, capsys):
    with patch("shadowforge.cli.AgentCoordinator.run", return_value=sample_run(executed=True)):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "--authorized",
                "agent",
                "Find services",
                "--target",
                "192.0.2.10",
                "--execute",
            ]
        )
    output = capsys.readouterr().out
    assert code == 0
    assert '"mode": "execute"' in output
    assert '"critique": "Looks sufficient."' in output


def test_cli_agent_reports_policy_and_model_errors(tmp_path, capsys):
    with patch(
        "shadowforge.cli.AgentCoordinator.run",
        side_effect=ProposalError("bad proposal"),
    ):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "agent",
                "Find services",
                "--target",
                "192.0.2.10",
            ]
        )
    assert code == 2
    assert "bad proposal" in capsys.readouterr().out

    with patch(
        "shadowforge.cli.AgentCoordinator.run",
        side_effect=ModelError("offline"),
    ):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "agent",
                "Find services",
                "--target",
                "192.0.2.10",
            ]
        )
    assert code == 2
    assert "offline" in capsys.readouterr().out
