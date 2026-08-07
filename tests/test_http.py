from unittest.mock import MagicMock, patch

import pytest

from shadowforge.tools.http import HttpMetadataTool, validate_http_arguments


def test_validate_http_arguments():
    assert validate_http_arguments({"scheme": "http", "port": 80}) == {
        "scheme": "http",
        "port": 80,
    }
    assert validate_http_arguments({"scheme": "https", "port": 443})["port"] == 443


@pytest.mark.parametrize(
    "arguments,match",
    [
        ({"scheme": "http"}, "exactly"),
        ({"scheme": "ftp", "port": 21}, "scheme"),
        ({"scheme": "http", "port": "80"}, "integer"),
        ({"scheme": "http", "port": True}, "integer"),
        ({"scheme": "http", "port": 0}, "integer"),
        ({"scheme": "http", "port": 65536}, "integer"),
    ],
)
def test_validate_http_arguments_rejects_invalid_values(arguments, match):
    with pytest.raises(ValueError, match=match):
        validate_http_arguments(arguments)


def test_http_probe_requires_single_ip():
    result = HttpMetadataTool().run("192.0.2.0/24", {"scheme": "http", "port": 80})
    assert result.status == "error"
    assert "one IP address" in result.data["error"]


def test_http_probe_collects_allowlisted_headers_only():
    response = MagicMock()
    response.status = 200
    response.reason = "OK"
    response.getheaders.return_value = [
        ("Server", "example"),
        ("Content-Type", "text/html"),
        ("Set-Cookie", "secret=value"),
    ]
    connection = MagicMock()
    connection.getresponse.return_value = response
    with patch("shadowforge.tools.http.http.client.HTTPConnection", return_value=connection):
        result = HttpMetadataTool().run("192.0.2.10", {"scheme": "http", "port": 80})
    assert result.status == "ok"
    assert result.data["status_code"] == 200
    assert result.data["headers"] == {"server": "example", "content-type": "text/html"}
    connection.request.assert_called_once_with(
        "HEAD",
        "/",
        headers={"User-Agent": "ShadowForge/0.3"},
    )
    connection.close.assert_called_once()


def test_https_probe_uses_bounded_tls_connection():
    response = MagicMock(status=301, reason="Moved")
    response.getheaders.return_value = [("Location", "https://example.test/")]
    connection = MagicMock()
    connection.getresponse.return_value = response
    context = MagicMock()
    with (
        patch("shadowforge.tools.http.ssl.create_default_context", return_value=context),
        patch("shadowforge.tools.http.http.client.HTTPSConnection", return_value=connection),
    ):
        result = HttpMetadataTool(timeout=2).run(
            "192.0.2.10",
            {"scheme": "https", "port": 443},
        )
    assert result.status == "ok"
    assert result.data["headers"] == {"location": "https://example.test/"}
    assert context.check_hostname is False
    connection.close.assert_called_once()


def test_http_probe_wraps_connection_error():
    connection = MagicMock()
    connection.request.side_effect = OSError("offline")
    with patch("shadowforge.tools.http.http.client.HTTPConnection", return_value=connection):
        result = HttpMetadataTool().run("192.0.2.10", {"scheme": "http", "port": 80})
    assert result.status == "error"
    assert "offline" in result.data["error"]
    connection.close.assert_called_once()
