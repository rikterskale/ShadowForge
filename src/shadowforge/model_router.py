"""Role-based model routing matching the ADAtlas local Ollama stack."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from shadowforge.models import OpenAICompatibleProvider


DEFAULT_MODELS: Mapping[str, str] = {
    "primary": "qwen3.5:27b",
    "critic": "gemma4:31b",
    "coding": "devstral-small-2:24b",
}


@dataclass(frozen=True)
class ModelRouter:
    """Create role-specific OpenAI-compatible clients for a local Ollama server."""

    base_url: str = "http://127.0.0.1:11434/v1"
    api_key: str = "ollama"
    timeout: float = 60.0

    def provider_for(self, role: str) -> OpenAICompatibleProvider:
        try:
            model = DEFAULT_MODELS[role]
        except KeyError as exc:
            raise KeyError(f"unknown model role: {role}") from exc
        return OpenAICompatibleProvider(
            base_url=self.base_url,
            model=model,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    @staticmethod
    def roles() -> tuple[str, ...]:
        return tuple(DEFAULT_MODELS)

    @staticmethod
    def config_path() -> Path:
        return Path("config/models.yaml")
