"""Provider routing for the two LLM decisions (safety screen, triage).

* `OpenAICompatClient` speaks the OpenAI chat-completions dialect (Groq, OpenRouter, Together, local servers...).
* `LLMRouter` gives each role (safety / triage) its own ordered chain of providers, so the two parallel calls can use
  different keys, and a failing or rate-limited provider falls through to the next one.
* A provider that answers 401/402/403/404/429 is skipped for a short cool-down so a dead key costs one failed call, not one per turn.

Errors never include request/response bodies or keys; they are what shows up in logs/failures.jsonl ("llm_errors").
"""
from __future__ import annotations

import dataclasses
import json
import logging
import re
import time
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import Settings, get_settings
from .gemini import GeminiClient, LLMError

log = logging.getLogger("carecompass.llm")
T = TypeVar("T", bound=BaseModel)
COOLDOWN_STATUS = {401: 300, 402: 300, 403: 300, 404: 300, 429: 45}  # seconds a provider is skipped after this HTTP status


class OpenAICompatClient:
    """Minimal OpenAI-compatible client with JSON-object output, validated against the same pydantic schema."""

    def __init__(self, name: str, api_key: str, base_url: str, model: str, settings: Settings | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.name, self.key, self.base, self._model = name, api_key, base_url.rstrip("/"), model
        self.s = settings or get_settings()
        self._transport = transport

    @property
    def enabled(self) -> bool:
        return bool(self.key and self.base and self._model) and self.s.llm_backend != "off"

    @property
    def model(self) -> str:
        return self._model

    def structured(self, system: str, user_text: str, schema: type[T], max_tokens: int = 900) -> T:
        hint = json.dumps(schema.model_json_schema(), separators=(",", ":"), ensure_ascii=False)
        body = {
            "model": self._model, "temperature": 0, "max_tokens": max(max_tokens, 1200),
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": f"{system}\n\nReturn ONLY one JSON object that validates against this JSON Schema "
                                              f"(no markdown, no extra keys, include every property):\n{hint}"},
                {"role": "user", "content": user_text},
            ],
        }
        url, headers = f"{self.base}/chat/completions", {"Authorization": f"Bearer {self.key}"}
        try:
            with httpx.Client(timeout=self.s.gemini_timeout_s, transport=self._transport) as c:
                r = c.post(url, json=body, headers=headers)
                if r.status_code in (429, 502, 503, 504):
                    time.sleep(_retry_after(r))
                    r = c.post(url, json=body, headers=headers)
            r.raise_for_status()
            choice = (r.json().get("choices") or [None])[0]
            if not choice or choice.get("finish_reason") not in (None, "stop"):
                raise LLMError(f"finish={choice and choice.get('finish_reason')}")
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", (choice["message"].get("content") or "").strip())
            return schema.model_validate(json.loads(text))
        except LLMError:
            raise
        except ValidationError as e:
            raise LLMError(f"schema:{e.error_count()} errors") from e
        except httpx.HTTPStatusError as e:
            raise LLMError(f"HTTP {e.response.status_code}") from e
        except (httpx.HTTPError, KeyError, IndexError, ValueError, TypeError) as e:
            raise LLMError(type(e).__name__) from e


def _retry_after(r: httpx.Response) -> float:
    try:
        return min(max(float(r.headers.get("retry-after", "0.4")), 0.2), 2.0)
    except ValueError:
        return 0.4


class _Role:
    """What a graph node holds: same interface as a single client, backed by an ordered provider chain."""

    def __init__(self, router: "LLMRouter", role: str, chain: list[str]):
        self.router, self.role, self.chain = router, role, chain

    @property
    def enabled(self) -> bool:
        return bool(self.chain)

    @property
    def model(self) -> str:
        return "+".join(f"{n}:{self.router.providers[n].model}" for n in self.chain) or "off"

    def structured(self, system: str, user_text: str, schema: type[T], max_tokens: int = 900) -> T:
        return self.router.call(self.chain, system, user_text, schema, max_tokens)


class LLMRouter:
    def __init__(self, providers: dict, chains: dict[str, list[str]], settings: Settings | None = None):
        self.providers = {n: c for n, c in providers.items() if c.enabled}
        self.chains = {role: [n for n in chain if n in self.providers] for role, chain in chains.items()}
        self._cool: dict[str, float] = {}

    @property
    def enabled(self) -> bool:
        return bool(self.providers)

    @property
    def model(self) -> str:
        return ", ".join(f"{role}={self.for_role(role).model}" for role in self.chains) or "off"

    def for_role(self, role: str) -> _Role:
        return _Role(self, role, self.chains.get(role) or list(self.providers))

    def structured(self, system: str, user_text: str, schema: type[T], max_tokens: int = 900) -> T:  # un-roled use
        return self.for_role("triage").structured(system, user_text, schema, max_tokens)

    def call(self, chain: list[str], system: str, user_text: str, schema: type[T], max_tokens: int) -> T:
        now = time.monotonic()
        order = [n for n in chain if self._cool.get(n, 0) <= now] or chain  # all cooling -> try anyway
        errors = []
        for name in order:
            try:
                out = self.providers[name].structured(system, user_text, schema, max_tokens)
                if errors:
                    log.warning("llm fallback: %s answered after %s", name, "; ".join(errors))
                return out
            except LLMError as e:
                errors.append(f"{name}: {e}")
                m = re.fullmatch(r"HTTP (\d+)", str(e))
                if m and int(m.group(1)) in COOLDOWN_STATUS:
                    self._cool[name] = time.monotonic() + COOLDOWN_STATUS[int(m.group(1))]
        raise LLMError("; ".join(errors) or "no provider")


def _names(raw: str) -> list[str]:
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def build_llm(settings: Settings | None = None) -> LLMRouter:
    s = settings or get_settings()
    providers = {
        "gemini": GeminiClient(s),
        "gemini2": GeminiClient(dataclasses.replace(s, gemini_api_key=s.gemini_api_key_2)),
        "groq": OpenAICompatClient("groq", s.groq_api_key, s.groq_base_url, s.groq_model, s),
        "compat": OpenAICompatClient("compat", s.compat_api_key, s.compat_base_url, s.compat_model, s),
    }
    live = [n for n, c in providers.items() if c.enabled]
    # Default: spread load. With 2+ providers the safety call starts on the first and the triage call on the second.
    default = {"safety": live, "triage": live[1:] + live[:1]}
    chains = {role: ([n for n in _names(raw) if n in live] or default[role])
              for role, raw in (("safety", s.llm_safety_chain), ("triage", s.llm_triage_chain))}
    return LLMRouter(providers, chains, s)
