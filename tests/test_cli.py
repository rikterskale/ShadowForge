import json
from unittest.mock import patch

from shadowforge.cli import main
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


def test_cli_models_full_stack(capsys):
    statuses = (
        ModelStatus("primary", "qwen3.5:27b", "qwen3.5:27b", False),
        ModelStatus("critic", "gemma4:31b", "gemma4:31b", False),
        ModelStatus("coding", "devstral-small-2:24b", "devstral-small-2:24b", False),
    )
    with patch("shadowforge.cli.ModelRouter.resolve", return_value=statuses):
        code = main(["models"])
    output = capsys.readouterr().out
    assert code == 0
    assert "FULL MODEL STACK" in output
    assert "[OK] primary" in output


def test_cli_models_qwen_only_fallback(capsys):
    statuses = (
        ModelStatus("primary", "qwen3.5:27b", "qwen3.5:27b", False),
        ModelStatus("critic", "gemma4:31b", "qwen3.5:27b", True),
        ModelStatus("coding", "devstral-small-2:24b", "qwen3.5:27b", True),
    )
    with patch("shadowforge.cli.ModelRouter.resolve", return_value=statuses):
        code = main(["models"])
    output = capsys.readouterr().out
    assert code == 0
    assert "QWEN-ONLY FALLBACK" in output
    assert "[FALLBACK] critic" in output
    assert "-> using qwen3.5:27b" in output


def test_cli_models_reports_missing_primary(capsys):
    with patch(
        "shadowforge.cli.ModelRouter.resolve",
        side_effect=ModelError("qwen3.5:27b is not installed"),
    ):
        code = main(["models"])
    assert code == 2
    assert "Model error" in capsys.readouterr().out
