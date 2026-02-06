"""Thin LiteLLM wrapper with safe fallback when dependency is unavailable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LiteLLMProvider:
    model: str
    temperature: float = 0.0
    max_tokens: int = 512

    def complete(self, *, system: str, user: str, **kwargs: Any) -> str:
        try:
            from litellm import completion
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "litellm is not installed. Install it to enable LLM inference."
            ) from exc

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            timeout=kwargs.get("timeout", 45),
        )
        choices = response.get("choices", []) if isinstance(response, dict) else []
        if not choices:
            return ""
        message = choices[0].get("message", {})
        return str(message.get("content", "")).strip()
