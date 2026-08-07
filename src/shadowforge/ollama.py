"""Minimal Ollama discovery client used for local model availability checks."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from shadowforge.models import ModelError


@dataclass(frozen=True)
class OllamaDiscovery:
    """Discover locally installed Ollama models without an extra dependency."""

    base_url: str = "http://127.0.0.1:11434/v1"
    timeout: float = 5.0

    def tags_url(self) -> str:
        root = self.base_url.rstrip("/")
        if root.endswith("/v1"):
            root = root[:-3]
        return root + "/api/tags"

    def available_models(self) -> frozenset[str]:
        request = urllib.request.Request(self.tags_url(), method="GET")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                payload = json.load(response)
            models = payload.get("models", [])
            if not isinstance(models, list):
                raise TypeError("'models' is not a list")
            names = {
                str(item.get("name") or item.get("model"))
                for item in models
                if isinstance(item, dict) and (item.get("name") or item.get("model"))
            }
            return frozenset(names)
        except (OSError, TypeError, ValueError) as exc:
            raise ModelError(f"could not query Ollama model inventory: {exc}") from exc
