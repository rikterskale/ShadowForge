import subprocess
from unittest.mock import patch

import pytest

from shadowforge.tools.nmap import NmapTool, validate_ports

XML = (
    "<?xml version='1.0'?><nmaprun><host><ports>"
    "<port protocol='tcp' portid='80'><state state='open'/>"
    "<service name='http' product='nginx' version='1.2'/></port>"
    "<port protocol='tcp' portid='81'><state state='closed'/></port>"
    "</ports></host></nmaprun>"
)


def test_nmap_command_is_constrained():
    assert NmapTool.build_command("192.0.2.1", {"ports": "22,80-81"}) == [
        "nmap",
        "-sT",
        "-sV",
        "--version-light",
        "-p",
        "22,80-81",
        "-oX",
        "-",
        "192.0.2.1",
    ]
    with pytest.raises(ValueError):
        NmapTool.build_command("192.0.2.1", {"ports": "80 --script vuln"})
    with pytest.raises(ValueError, match="string"):
        NmapTool.build_command("192.0.2.1", {"ports": 80})


def test_port_expression_validation():
    assert validate_ports("1,22,80-443,65535") == "1,22,80-443,65535"
    invalid = ["", "80,,443", "80-", "-443", "80-90-100", "0", "65536", "443-80"]
    for value in invalid:
        with pytest.raises(ValueError):
            validate_ports(value)


def test_nmap_missing_binary():
    with patch("shadowforge.tools.nmap.shutil.which", return_value=None):
        result = NmapTool().run("192.0.2.1", {})
    assert result.status == "error"


def test_nmap_parses_services():
    completed = subprocess.CompletedProcess([], 0, stdout=XML, stderr="")
    with patch("shadowforge.tools.nmap.shutil.which", return_value="/usr/bin/nmap"), patch(
        "shadowforge.tools.nmap.subprocess.run", return_value=completed
    ):
        result = NmapTool().run("192.0.2.1", {})
    assert result.data["services"] == [
        {
            "port": 80,
            "protocol": "tcp",
            "service": "http",
            "product": "nginx",
            "version": "1.2",
        }
    ]


def test_nmap_error_paths():
    tool = NmapTool(timeout=1)
    with patch("shadowforge.tools.nmap.shutil.which", return_value="nmap"), patch(
        "shadowforge.tools.nmap.subprocess.run", side_effect=subprocess.TimeoutExpired("nmap", 1)
    ):
        assert tool.run("192.0.2.1", {}).status == "error"
    with patch("shadowforge.tools.nmap.shutil.which", return_value="nmap"), patch(
        "shadowforge.tools.nmap.subprocess.run", side_effect=OSError("permission denied")
    ):
        assert "could not start nmap" in tool.run("192.0.2.1", {}).data["error"]
    failed = subprocess.CompletedProcess([], 2, stdout="", stderr="boom")
    with patch("shadowforge.tools.nmap.shutil.which", return_value="nmap"), patch(
        "shadowforge.tools.nmap.subprocess.run", return_value=failed
    ):
        assert tool.run("192.0.2.1", {}).data["returncode"] == 2
    malformed = subprocess.CompletedProcess([], 0, stdout="<bad", stderr="")
    with patch("shadowforge.tools.nmap.shutil.which", return_value="nmap"), patch(
        "shadowforge.tools.nmap.subprocess.run", return_value=malformed
    ):
        assert tool.run("192.0.2.1", {}).status == "error"
