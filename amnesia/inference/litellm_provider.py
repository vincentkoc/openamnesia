"""Thin LiteLLM wrapper with safe fallback when dependency is unavailable."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class LiteLLMProvider:
    model: str
    temperature: float = 0.0
    max_tokens: int = 512

    def complete(self, *, system: str, user: str, **kwargs: Any) -> str:
        os.environ.setdefault("LITELLM_LOG", "ERROR")
        logging.getLogger("LiteLLM").setLevel(logging.ERROR)
        logging.getLogger("litellm").setLevel(logging.ERROR)
        try:
            import litellm
            from litellm import completion
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "litellm is not installed. Install it to enable LLM inference."
            ) from exc

        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = True
        if hasattr(litellm, "set_verbose"):
            litellm.set_verbose = False

        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "timeout": kwargs.get("timeout", 45),
            "drop_params": True,
        }
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        if str(self.model).startswith("gpt-5"):
            request["max_completion_tokens"] = max_tokens
        else:
            request["max_tokens"] = max_tokens
            request["temperature"] = kwargs.get("temperature", self.temperature)

        response = completion(**request)
        if isinstance(response, dict):
            choices = response.get("choices", []) or []
        else:
            choices = getattr(response, "choices", []) or []
        if not choices:
            return ""
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message", {})
        else:
            message = getattr(first, "message", {})

        if isinstance(message, dict):
            content = message.get("content", "")
        else:
            content = getattr(message, "content", "")

        if isinstance(content, list):
            chunks: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text = item.get("text")
                    if text:
                        chunks.append(str(text))
                else:
                    text = getattr(item, "text", None)
                    if text:
                        chunks.append(str(text))
            content = "\n".join(chunks)
        return str(content or "").strip()
