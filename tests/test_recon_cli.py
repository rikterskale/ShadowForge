import json
from unittest.mock import patch

from shadowforge.cli import main
from shadowforge.models import ModelError
from shadowforge.recon import ReconAction, ReconDecisionError, ReconRun, ReconStep
from shadowforge.tools.base import ToolResult


def scope_file(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "lab", "targets": ["192.0.2.0/24"]}))
    return path


def run_result(*, executed=False, failed=False, critic_error=None):
    action = ReconAction(
        "nmap_service_scan",
        "192.0.2.10",
        {"ports": "22,80,443"},
        "Identify common services.",
    )
    result = ToolResult("error" if failed else "ok", {"services": []}) if executed else None
    step = ReconStep(1, action, result)
    return ReconRun(
        steps=(step,),
        summary="Done" if executed else None,
        critique=None if critic_error else ("Reviewed" if executed else None),
        critique_error=critic_error,
        budget_exhausted=executed,
    )


def test_recon_requires_scope(capsys):
    assert main(["recon", "Find services", "--target", "192.0.2.10"]) == 2
    assert "recon mode requires --scope" in capsys.readouterr().out


def test_recon_execute_requires_authorized(tmp_path, capsys):
    code = main(
        [
            "--scope",
            str(scope_file(tmp_path)),
            "recon",
            "Find services",
            "--target",
            "192.0.2.10",
            "--execute",
        ]
    )
    assert code == 2
    assert "Refusing to execute" in capsys.readouterr().out


def test_recon_dry_run_prints_first_step(tmp_path, capsys):
    with patch("shadowforge.cli.ReconCoordinator.run", return_value=run_result()):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "recon",
                "Find services",
                "--target",
                "192.0.2.10",
                "--max-steps",
                "4",
            ]
        )
    output = capsys.readouterr().out
    assert code == 0
    assert '"mode": "dry-run"' in output
    assert '"nmap_service_scan"' in output


def test_recon_execute_prints_summary_critique_and_budget(tmp_path, capsys):
    with patch("shadowforge.cli.ReconCoordinator.run", return_value=run_result(executed=True)):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "--authorized",
                "recon",
                "Find services",
                "--target",
                "192.0.2.10",
                "--execute",
            ]
        )
    output = capsys.readouterr().out
    assert code == 0
    assert '"summary": "Done"' in output
    assert '"critique": "Reviewed"' in output
    assert '"budget_exhausted": true' in output


def test_recon_preserves_critic_error(tmp_path, capsys):
    run = run_result(executed=True, critic_error="critic offline")
    with patch("shadowforge.cli.ReconCoordinator.run", return_value=run):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "--authorized",
                "recon",
                "Find services",
                "--target",
                "192.0.2.10",
                "--execute",
            ]
        )
    assert code == 0
    assert '"critique_error": "critic offline"' in capsys.readouterr().out


def test_recon_returns_one_when_any_step_fails(tmp_path):
    with patch(
        "shadowforge.cli.ReconCoordinator.run",
        return_value=run_result(executed=True, failed=True),
    ):
        code = main(
            [
                "--scope",
                str(scope_file(tmp_path)),
                "--authorized",
                "recon",
                "Find services",
                "--target",
                "192.0.2.10",
                "--execute",
            ]
        )
    assert code == 1


def test_recon_reports_policy_model_and_file_errors(tmp_path, capsys):
    base = [
        "--scope",
        str(scope_file(tmp_path)),
        "recon",
        "Find services",
        "--target",
        "192.0.2.10",
    ]
    with patch(
        "shadowforge.cli.ReconCoordinator.run",
        side_effect=ReconDecisionError("bad decision"),
    ):
        assert main(base) == 2
    assert "bad decision" in capsys.readouterr().out

    with patch("shadowforge.cli.ReconCoordinator.run", side_effect=ModelError("offline")):
        assert main(base) == 2
    assert "offline" in capsys.readouterr().out

    with patch("shadowforge.cli.ReconCoordinator.run", side_effect=OSError("disk error")):
        assert main(base) == 2
    assert "File/system error: disk error" in capsys.readouterr().out
