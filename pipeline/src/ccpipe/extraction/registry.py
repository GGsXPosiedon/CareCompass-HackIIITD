"""Concept registry loader. Variants are tokenised exactly like input text."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from ..paths import load_yaml

# Letters, digits, apostrophes, and Devanagari (excluding the danda punctuation U+0964/0965).
TOKEN_RE = re.compile(r"[A-Za-z0-9'’ऀ-ॣ०-ॿ]+")
_NUKTA = "़"
_CHANDRABINDU = "ँ"
_ANUSVARA = "ं"


class RegistryError(ValueError):
    pass


def norm_token(tok: str) -> str:
    tok = unicodedata.normalize("NFC", tok).lower().replace("’", "'")
    tok = tok.replace(_NUKTA, "").replace(_CHANDRABINDU, _ANUSVARA)
    tok = tok.strip("'")
    if tok.endswith("'s"):
        tok = tok[:-2]
    return tok


def tokenize(text: str) -> list[tuple[str, int, int]]:
    """Return (normalised_token, start, end) with offsets into the ORIGINAL text."""
    return [(norm_token(m.group()), m.start(), m.end()) for m in TOKEN_RE.finditer(text)]


@dataclass(frozen=True)
class Concept:
    id: str
    category: str
    generic: bool
    variants: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Registry:
    version: str
    review_status: str
    concepts: dict[str, Concept]
    by_first_token: dict[str, list[tuple[tuple[str, ...], str]]]  # sorted longest-first
    relations: dict[str, str]  # token -> relation
    first_person: frozenset[str]
    third_person: frozenset[str]


_CATEGORIES = {"symptom", "request", "context"}


def _tok_seq(phrase: str) -> tuple[str, ...]:
    seq = tuple(t for t, _, _ in tokenize(phrase))
    if not seq:
        raise RegistryError(f"empty variant: {phrase!r}")
    return seq


def load_registry() -> Registry:
    cfg = load_yaml("concepts.yaml")
    concepts: dict[str, Concept] = {}
    owner: dict[tuple[str, ...], str] = {}
    index: dict[str, list[tuple[tuple[str, ...], str]]] = {}
    for cid, spec in cfg["concepts"].items():
        if spec["category"] not in _CATEGORIES:
            raise RegistryError(f"{cid}: bad category {spec['category']!r}")
        seqs: list[tuple[str, ...]] = []
        for lang in ("en", "hi", "hinglish"):
            for phrase in spec.get(lang, []) or []:
                seq = _tok_seq(phrase)
                if owner.get(seq, cid) != cid:
                    raise RegistryError(f"variant {phrase!r} belongs to both {owner[seq]} and {cid}")
                owner[seq] = cid
                if seq not in seqs:
                    seqs.append(seq)
        if not seqs:
            raise RegistryError(f"{cid}: no variants")
        concepts[cid] = Concept(cid, spec["category"], bool(spec.get("generic", False)), tuple(seqs))
        for seq in seqs:
            index.setdefault(seq[0], []).append((seq, cid))
    for entries in index.values():
        entries.sort(key=lambda e: -len(e[0]))
    relations: dict[str, str] = {}
    for rel, words in cfg["relations"].items():
        for w in words:
            relations[norm_token(w)] = rel
    return Registry(
        version=cfg["version"], review_status=cfg["review_status"], concepts=concepts,
        by_first_token=index, relations=relations,
        first_person=frozenset(norm_token(w) for w in cfg["first_person"]),
        third_person=frozenset(norm_token(w) for w in cfg["third_person"]),
    )
