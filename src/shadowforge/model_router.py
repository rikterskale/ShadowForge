"""Role-based model routing matching the ADAtlas local Ollama stack."""

from __future__ import annotations

from dataclasses import dataclass

from shadowforge.models import ModelError, OpenAICompatibleProvider
from shadowforge.ollama import OllamaDiscovery

DEFAULT_MODELS: dict[str, str] = {
    "primary": "qwen3.5:27b",
    "critic": "gemma4:31b",
    "coding": "devstral-small-2:24b",
}
PRIMARY_ROLE = "primary"


@dataclass(frozen=True)
class ModelStatus:
    role: str
    preferred_model: str
    active_model: str
    fallback: bool
    fallback_reason: str | None


@dataclass(frozen=True)
class ModelRouter:
    """Create role-specific clients with Qwen fallback for optional specialists."""

    base_url: str = "http://127.0.0.1:11434/v1"
    api_key: str = "ollama"
    timeout: float = 60.0
    discovery_timeout: float = 5.0

    def _available_models(self) -> frozenset[str]:
        return OllamaDiscovery(
            base_url=self.base_url,
            timeout=self.discovery_timeout,
        ).available_models()

    def resolve(self, available_models: frozenset[str] | None = None) -> tuple[ModelStatus, ...]:
        available = self._available_models() if available_models is None else available_models
        primary = DEFAULT_MODELS[PRIMARY_ROLE]
        if primary not in available:
            raise ModelError(
                f"required primary model {primary!r} is not installed in Ollama; "
                f"install it with: ollama pull {primary}"
            )
        statuses: list[ModelStatus] = []
        for role, preferred in DEFAULT_MODELS.items():
            active = preferred if preferred in available else primary
            fallback = active != preferred
            statuses.append(
                ModelStatus(
                    role=role,
                    preferred_model=preferred,
                    active_model=active,
                    fallback=fallback,
                    fallback_reason=(
                        f"{preferred} is not installed; using required primary model {primary}"
                        if fallback
                        else None
                    ),
                )
            )
        return tuple(statuses)

    def provider_for(
        self,
        role: str,
        available_models: frozenset[str] | None = None,
    ) -> OpenAICompatibleProvider:
        if role not in DEFAULT_MODELS:
            raise KeyError(f"unknown model role: {role}")
        statuses = {status.role: status for status in self.resolve(available_models)}
        return OpenAICompatibleProvider(
            base_url=self.base_url,
            model=statuses[role].active_model,
            api_key=self.api_key,
            timeout=self.timeout,
        )

    @staticmethod
    def roles() -> tuple[str, ...]:
        return tuple(DEFAULT_MODELS)
