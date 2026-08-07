"""LLM provider abstractions."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class ModelError(RuntimeError):
    """Raised when the configured model provider cannot return a response."""


class ModelProvider(Protocol):
    def complete(self, system_prompt: str, user_prompt: str) -> str: ...


@dataclass
class OpenAICompatibleProvider:
    """Small dependency-free client for OpenAI-compatible chat-completions endpoints."""

    base_url: str
    model: str
    api_key: str = ""
    timeout: float = 60.0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0,
            }
        ).encode()
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
                payload = json.load(response)
            content = payload["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise TypeError("response message content is not a string")
            return content
        except (OSError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelError(f"model request failed: {exc}") from exc
