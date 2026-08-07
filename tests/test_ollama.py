import io
from unittest.mock import patch

import pytest

from shadowforge.models import ModelError
from shadowforge.ollama import OllamaDiscovery


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_tags_url_handles_openai_compatible_suffix():
    assert OllamaDiscovery().tags_url() == "http://127.0.0.1:11434/api/tags"
    assert OllamaDiscovery("http://localhost:11434").tags_url() == "http://localhost:11434/api/tags"


def test_available_models_parses_name_and_model_fields():
    payload = b'{"models":[{"name":"qwen3.5:27b"},{"model":"gemma4:31b"},{"x":1}]}'
    with patch("shadowforge.ollama.urllib.request.urlopen", return_value=Response(payload)):
        models = OllamaDiscovery().available_models()
    assert models == frozenset({"qwen3.5:27b", "gemma4:31b"})


def test_available_models_reports_connection_and_payload_errors():
    with (
        patch("shadowforge.ollama.urllib.request.urlopen", side_effect=OSError("offline")),
        pytest.raises(ModelError, match="could not query Ollama"),
    ):
        OllamaDiscovery().available_models()
    with (
        patch(
            "shadowforge.ollama.urllib.request.urlopen",
            return_value=Response(b'{"models":{}}'),
        ),
        pytest.raises(ModelError, match="could not query Ollama"),
    ):
        OllamaDiscovery().available_models()
