"""Small, deterministic text helpers."""
from __future__ import annotations

import unicodedata


def normalize_text(text: str) -> str:
    """NFC + collapsed whitespace. Does not lowercase, translate or strip negations."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def detect_script(text: str) -> str:
    deva = sum(1 for ch in text if "ऀ" <= ch <= "ॿ")
    latin = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    if deva and latin:
        return "mixed"
    if deva:
        return "devanagari"
    if latin:
        return "latin"
    return "unknown"
