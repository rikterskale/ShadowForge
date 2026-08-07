"""Bounded HTTP metadata probe for authorized reconnaissance."""

from __future__ import annotations

import http.client
import ipaddress
import ssl
from typing import Any

from shadowforge.tools.base import ToolResult

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_HEADER_ALLOWLIST = frozenset(
    {"server", "content-type", "content-length", "location", "allow", "x-powered-by"}
)


def validate_http_arguments(arguments: dict[str, Any]) -> dict[str, str | int]:
    if not isinstance(arguments, dict) or set(arguments) != {"scheme", "port"}:
        raise ValueError("HTTP arguments must contain exactly: scheme, port")
    scheme = arguments["scheme"]
    port = arguments["port"]
    if not isinstance(scheme, str) or scheme not in _ALLOWED_SCHEMES:
        raise ValueError("HTTP scheme must be 'http' or 'https'")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("HTTP port must be an integer between 1 and 65535")
    return {"scheme": scheme, "port": port}


class HttpMetadataTool:
    """Issue one HEAD request to '/' without redirects or arbitrary paths."""

    name = "http_metadata_probe"

    def __init__(self, *, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def run(self, target: str, arguments: dict[str, Any]) -> ToolResult:
        try:
            ipaddress.ip_address(target)
        except ValueError:
            return ToolResult(
                status="error",
                data={"error": "HTTP metadata probe requires one IP address, not a CIDR"},
            )
        validated = validate_http_arguments(arguments)
        scheme = str(validated["scheme"])
        port = int(validated["port"])
        connection: http.client.HTTPConnection
        if scheme == "https":
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            connection = http.client.HTTPSConnection(
                target,
                port,
                timeout=self.timeout,
                context=context,
            )
        else:
            connection = http.client.HTTPConnection(target, port, timeout=self.timeout)
        try:
            connection.request("HEAD", "/", headers={"User-Agent": "ShadowForge/0.3"})
            response = connection.getresponse()
            headers = {
                key.lower(): value
                for key, value in response.getheaders()
                if key.lower() in _HEADER_ALLOWLIST
            }
            return ToolResult(
                status="ok",
                data={
                    "scheme": scheme,
                    "port": port,
                    "status_code": response.status,
                    "reason": response.reason,
                    "headers": headers,
                },
            )
        except (OSError, http.client.HTTPException) as exc:
            return ToolResult(status="error", data={"error": f"HTTP probe failed: {exc}"})
        finally:
            connection.close()
