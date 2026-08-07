import io
from unittest.mock import patch

import pytest

from shadowforge.models import ModelError, OpenAICompatibleProvider


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def test_openai_compatible_provider():
    provider = OpenAICompatibleProvider("http://localhost:8000/v1", "model", "key")
    response = Response(b'{"choices":[{"message":{"content":"hello"}}]}')
    with patch("shadowforge.models.urllib.request.urlopen", return_value=response):
        assert provider.complete("system", "user") == "hello"


def test_openai_compatible_provider_errors():
    provider = OpenAICompatibleProvider("http://localhost:8000/v1", "model")
    with patch("shadowforge.models.urllib.request.urlopen", side_effect=OSError("offline")):
        with pytest.raises(ModelError):
            provider.complete("system", "user")
