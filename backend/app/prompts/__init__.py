"""Versioned system prompts. Each .md file has a small front-matter header (id, version, node, schema)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Prompt:
    id: str
    version: str
    text: str

    @property
    def tag(self) -> str:
        return f"{self.id}@{self.version}"


@lru_cache
def load(name: str) -> Prompt:
    raw = (DIR / f"{name}.md").read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw
    if raw.startswith("---"):
        head, body = raw[3:].split("---", 1)
        for line in head.strip().splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return Prompt(meta.get("id", name), meta.get("version", "0"), body.strip())


def render_case(*, language: str, history: list[dict], message: str, profile: dict | None, follow_ups_asked: int) -> str:
    """The per-request user turn. Untrusted text is fenced in tags the system prompt tells the model not to obey."""
    hist = "\n".join(f"{t['role']}: {' '.join(t['content'].split())[:400]}" for t in history[-8:]) or "(none)"
    prof = json.dumps(profile, ensure_ascii=False)[:6000] if profile and profile.get("members") else "null"
    return (
        f"user_language: {language}\n"
        f"follow_up_questions_already_asked: {follow_ups_asked}\n"
        f"PROFILE: {prof}\n"
        f"<history>\n{hist}\n</history>\n"
        f"<user_message>\n{' '.join(message.split())[:1500]}\n</user_message>"
    )
