import json
from unittest.mock import patch

from shadowforge.cli import main
from shadowforge.tools.base import ToolResult


def scope_file(tmp_path):
    path = tmp_path / "scope.json"
    path.write_text(json.dumps({"name": "lab", "targets": ["192.0.2.0/24"]}))
    return path


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
