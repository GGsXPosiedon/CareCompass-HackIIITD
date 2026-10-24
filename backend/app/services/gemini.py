"""Minimal Gemini REST client with schema-enforced JSON output (no SDK, no key in URLs or logs)."""
from __future__ import annotations

import json
import logging
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import Settings, get_settings
from ..schemas.llm import gemini_schema

log = logging.getLogger("carecompass.llm")
T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """Any failure (network, HTTP, safety block, bad JSON, schema violation). Callers fall back."""


class GeminiClient:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, settings: Settings | None = None, transport: httpx.BaseTransport | None = None):
        self.s = settings or get_settings()
        self._transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.s.gemini_api_key) and self.s.llm_backend != "off"

    @property
    def model(self) -> str:
        return self.s.gemini_model

    def structured(self, system: str, user_text: str, schema: type[T], max_tokens: int = 900) -> T:
        gen: dict = {
            "temperature": 0,
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema(schema),
            "maxOutputTokens": max_tokens,
        }
        if self.model.startswith("gemini-3"):
            gen["thinkingConfig"] = {"thinkingLevel": self.s.gemini_thinking_level}
            gen["maxOutputTokens"] = max(4096, max_tokens)
        elif self.s.gemini_thinking_budget >= 0:
            gen["thinkingConfig"] = {"thinkingBudget": self.s.gemini_thinking_budget}
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
            "generationConfig": gen,
        }
        try:
            with httpx.Client(timeout=self.s.gemini_timeout_s, transport=self._transport) as c:
                r = c.post(self.URL.format(model=self.model), json=body, headers={"x-goog-api-key": self.s.gemini_api_key})
                if r.status_code in (502, 503, 504):
                    time.sleep(0.3)
                    r = c.post(self.URL.format(model=self.model), json=body, headers={"x-goog-api-key": self.s.gemini_api_key})
            r.raise_for_status()
            payload = r.json()
            cand = (payload.get("candidates") or [None])[0]
            if not cand or cand.get("finishReason") not in (None, "STOP"):
                raise LLMError(f"finish={cand and cand.get('finishReason')}")
            text = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
            return schema.model_validate(json.loads(text))
        except LLMError:
            raise
        except ValidationError as e:
            raise LLMError(f"schema:{e.error_count()} errors") from e
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}") from e
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as e:
            raise LLMError(type(e).__name__) from e  # never include body/key
