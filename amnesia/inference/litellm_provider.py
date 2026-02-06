"""Thin LiteLLM wrapper with safe fallback when dependency is unavailable."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, TypeVar

TModel = TypeVar("TModel")
_LITELLM_LOGGING_CONFIGURED = False


@dataclass(slots=True)
class LiteLLMProvider:
    model: str
    temperature: float = 0.0
    max_tokens: int = 512
    max_retries: int = 3
    retry_min_seconds: float = 0.5
    retry_max_seconds: float = 4.0
    throttle_seconds: float = 0.0

    def complete(self, *, system: str, user: str, **kwargs: Any) -> str:
        response = self._completion_with_retries(
            system=system,
            user=user,
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            timeout=kwargs.get("timeout", 45),
        )
        content = _extract_text_content(response)
        if content:
            return content
        raise RuntimeError(f"LLM returned no text content ({_response_diagnostics(response)})")

    def complete_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[TModel],
        **kwargs: Any,
    ) -> TModel:
        max_tokens = max(int(kwargs.get("max_tokens", self.max_tokens)), 256)
        timeout = kwargs.get("timeout", 45)

        # Attempt 1: strict JSON mode.
        response = self._completion_with_retries(
            system=system,
            user=user,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format={"type": "json_object"},
        )
        content = _extract_text_content(response)
        if content:
            json_payload = _extract_json_text(content)
            if json_payload:
                return _validate_model(response_model, json_payload)
        if _is_length_finish(response):
            expanded_tokens = max(int(max_tokens) * 3, 256)
            retry_response = self._completion_with_retries(
                system=system,
                user=user,
                max_tokens=expanded_tokens,
                timeout=timeout,
                response_format={"type": "json_object"},
            )
            retry_content = _extract_text_content(retry_response)
            if retry_content:
                retry_json_payload = _extract_json_text(retry_content)
                if retry_json_payload:
                    return _validate_model(response_model, retry_json_payload)
            response = retry_response

        # Attempt 2: fallback without response_format for providers/models that
        # ignore JSON mode on chat completions.
        fallback_system = (
            f"{system}\n"
            "Return ONLY one JSON object matching the schema. No markdown, no prose."
        )
        fallback_response = self._completion_with_retries(
            system=fallback_system,
            user=user,
            max_tokens=max_tokens,
            timeout=timeout,
            response_format=None,
        )
        fallback_content = _extract_text_content(fallback_response)
        if not fallback_content:
            raise RuntimeError(
                "LLM returned no text content in structured mode "
                f"(json_mode={_response_diagnostics(response)}; "
                f"fallback={_response_diagnostics(fallback_response)})"
            )
        fallback_json = _extract_json_text(fallback_content)
        if not fallback_json:
            raise RuntimeError(
                "Structured response missing JSON payload "
                f"(fallback_text={fallback_content[:180]!r})"
            )
        return _validate_model(response_model, fallback_json)

    def _completion_with_retries(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        timeout: int,
        response_format: dict[str, str] | None = None,
    ) -> object:
        _configure_litellm_logging()
        logger = logging.getLogger(__name__)
        try:
            import litellm
            from litellm import completion
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "litellm is not installed. Install it to enable LLM inference."
            ) from exc

        trace_enabled = os.getenv("AMNESIA_LITELLM_TRACE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }
        if hasattr(litellm, "suppress_debug_info"):
            litellm.suppress_debug_info = not trace_enabled
        if hasattr(litellm, "set_verbose"):
            litellm.set_verbose = trace_enabled

        request: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "timeout": timeout,
            "drop_params": True,
        }
        if response_format is not None:
            request["response_format"] = response_format
        if str(self.model).startswith("gpt-5"):
            request["max_completion_tokens"] = max(max_tokens, 256)
            request["reasoning_effort"] = kwargs_reasoning_effort()
        else:
            request["max_tokens"] = max_tokens
            request["temperature"] = self.temperature

        attempts = max(1, int(self.max_retries))
        last_error: Exception | None = None
        for attempt in range(1, attempts + 1):
            if self.throttle_seconds > 0:
                time.sleep(self.throttle_seconds)
            try:
                return completion(**request)
            except Exception as exc:  # pragma: no cover
                last_error = exc
                if attempt >= attempts:
                    break
                delay = min(self.retry_max_seconds, self.retry_min_seconds * (2 ** (attempt - 1)))
                logger.debug(
                    "event=llm_retry model=%s attempt=%d/%d delay=%.2fs error=%s",
                    self.model,
                    attempt,
                    attempts,
                    delay,
                    str(exc)[:320],
                )
                time.sleep(delay)
        raise RuntimeError(f"LLM request failed after {attempts} attempts: {last_error}")


def _extract_text_content(response: object) -> str:
    parts: list[str] = []

    output_text = _maybe_get(response, "output_text")
    if isinstance(output_text, str) and output_text.strip():
        parts.append(output_text.strip())

    choices = _maybe_get(response, "choices")
    if isinstance(choices, list):
        for choice in choices:
            message = _maybe_get(choice, "message")
            if message is None:
                continue
            content = _maybe_get(message, "content")
            parts.extend(_extract_content_parts(content))

    output = _maybe_get(response, "output")
    if isinstance(output, list):
        for item in output:
            content = _maybe_get(item, "content")
            if content is None:
                continue
            parts.extend(_extract_content_parts(content))

    merged = "\n".join(part.strip() for part in parts if str(part).strip())
    return merged.strip()


def _extract_content_parts(content: object) -> list[str]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            text = _maybe_get(item, "text")
            if isinstance(text, str) and text.strip():
                chunks.append(text)
        return chunks
    text = _maybe_get(content, "text")
    if isinstance(text, str) and text.strip():
        return [text]
    return []


def _maybe_get(value: object, key: str) -> object:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _response_diagnostics(response: object) -> str:
    model = _maybe_get(response, "model")
    choices = _maybe_get(response, "choices")
    output = _maybe_get(response, "output")
    output_text = _maybe_get(response, "output_text")
    finish_reason = _finish_reason(response)
    refusal = None
    if isinstance(choices, list) and choices:
        message = _maybe_get(choices[0], "message")
        refusal = _maybe_get(message, "refusal")
    choice_count = len(choices) if isinstance(choices, list) else 0
    output_count = len(output) if isinstance(output, list) else 0
    has_output_text = bool(isinstance(output_text, str) and output_text.strip())
    return (
        f"model={model!r}, choices={choice_count}, output={output_count}, "
        f"has_output_text={has_output_text}, finish_reason={finish_reason!r}, "
        f"refusal={bool(refusal)}"
    )


def _finish_reason(response: object) -> str | None:
    choices = _maybe_get(response, "choices")
    if isinstance(choices, list) and choices:
        value = _maybe_get(choices[0], "finish_reason")
        return str(value) if value is not None else None
    return None


def _is_length_finish(response: object) -> bool:
    reason = _finish_reason(response)
    if reason is None:
        return False
    return reason.lower() == "length"


def _extract_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1].strip()
    return ""


def _validate_model(response_model: type[TModel], json_payload: str) -> TModel:
    try:
        return response_model.model_validate_json(json_payload)
    except Exception:
        data = json.loads(json_payload)
        return response_model.model_validate(data)


def _configure_litellm_logging() -> None:
    global _LITELLM_LOGGING_CONFIGURED
    requested = os.getenv("AMNESIA_LITELLM_LOG_LEVEL", "").strip().upper()
    if requested not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        requested = "WARNING"
    trace_enabled = os.getenv("AMNESIA_LITELLM_TRACE", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    # Prevent request/body spam unless trace is explicitly enabled.
    effective = "INFO" if requested == "DEBUG" and not trace_enabled else requested
    os.environ["LITELLM_LOG"] = effective
    level = getattr(logging, effective, logging.WARNING)
    for name in ("LiteLLM", "litellm"):
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = True
        if trace_enabled:
            continue
        if not _LITELLM_LOGGING_CONFIGURED:
            logger.addFilter(_LiteLLMNoiseFilter())
    _LITELLM_LOGGING_CONFIGURED = True


class _LiteLLMNoiseFilter(logging.Filter):
    _drop_substrings = (
        "POST Request Sent from LiteLLM",
        "Request to litellm:",
        "checking potential_model_names in litellm.model_cost",
        "curl -X POST",
        "self.optional_params:",
        "RAW RESPONSE:",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        text = str(record.getMessage())
        return not any(token in text for token in self._drop_substrings)


def kwargs_reasoning_effort() -> str:
    raw = os.getenv("AMNESIA_LLM_REASONING_EFFORT", "").strip().lower()
    if raw in {"minimal", "low", "medium", "high"}:
        return raw
    return "minimal"
