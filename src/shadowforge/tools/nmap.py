"""Non-destructive Nmap service-discovery adapter."""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from typing import Any

from shadowforge.tools.base import ToolResult


def validate_ports(value: str) -> str:
    """Validate a comma-separated list of ports and ascending port ranges."""

    if not isinstance(value, str) or not value:
        raise ValueError("ports must be a non-empty numeric port expression")
    for item in value.split(","):
        if not item:
            raise ValueError("ports must not contain empty entries")
        pieces = item.split("-")
        if len(pieces) not in {1, 2} or any(not piece.isdigit() for piece in pieces):
            raise ValueError(
                "ports must contain only individual ports or ranges such as "
                "80,443,8000-8100"
            )
        numbers = [int(piece) for piece in pieces]
        if any(number < 1 or number > 65535 for number in numbers):
            raise ValueError("ports must be between 1 and 65535")
        if len(numbers) == 2 and numbers[0] > numbers[1]:
            raise ValueError("port ranges must be in ascending order")
    return value


class NmapTool:
    name = "nmap_service_scan"

    def __init__(self, *, timeout: int = 300) -> None:
        self.timeout = timeout

    @staticmethod
    def build_command(target: str, arguments: dict[str, Any]) -> list[str]:
        ports = arguments.get("ports", "1-1024")
        if not isinstance(ports, str):
            raise ValueError("ports must be a string")
        validate_ports(ports)
        return ["nmap", "-sT", "-sV", "--version-light", "-p", ports, "-oX", "-", target]

    def run(self, target: str, arguments: dict[str, Any]) -> ToolResult:
        if shutil.which("nmap") is None:
            return ToolResult(status="error", data={"error": "nmap is not installed"})
        command = self.build_command(target, arguments)
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(status="error", data={"error": "nmap timed out"})
        except OSError as exc:
            return ToolResult(status="error", data={"error": f"could not start nmap: {exc}"})
        if completed.returncode != 0:
            return ToolResult(
                status="error",
                data={"returncode": completed.returncode, "stderr": completed.stderr.strip()},
            )
        try:
            root = ET.fromstring(completed.stdout)
        except ET.ParseError as exc:
            return ToolResult(status="error", data={"error": f"invalid nmap XML: {exc}"})
        services: list[dict[str, Any]] = []
        for port in root.findall(".//port"):
            state = port.find("state")
            service = port.find("service")
            if state is None or state.get("state") != "open":
                continue
            services.append(
                {
                    "port": int(port.get("portid", "0")),
                    "protocol": port.get("protocol", "unknown"),
                    "service": service.get("name", "unknown") if service is not None else "unknown",
                    "product": service.get("product", "") if service is not None else "",
                    "version": service.get("version", "") if service is not None else "",
                }
            )
        return ToolResult(status="ok", data={"services": services})
