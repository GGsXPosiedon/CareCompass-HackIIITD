"""Meaning-based safety net: catches life-threat wording the regex rules do not list.

It compares the message with reviewed example phrasings per red flag (app/rules/safety_exemplars.json) and with
benign counter-examples. Two interchangeable embedders:
  * "ngram" (default): hashed character 2-5 gram TF-IDF vectors. Pure python, no downloads, tolerant of typos and
    Hinglish spelling variation, but only lexically similar.
  * "e5": multilingual-e5 sentence embeddings (needs torch + sentence-transformers + a local model folder); also
    generalises across paraphrases and languages. Select with SEMANTIC_EMBEDDER=e5 and SEMANTIC_MODEL_DIR=<path>.
It can only RAISE urgency (never lower a rules decision) and fires only if the best positive clearly beats the
best benign counter-example. DRAFT: exemplars and thresholds are not clinically validated.
"""
from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import zlib
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

EXEMPLARS = Path(__file__).resolve().parents[1] / "rules" / "safety_exemplars.json"
DIM = 1 << 16


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).lower()
    t = re.sub(r"(.)\1{2,}", r"\1\1", t)  # "bleeeding" -> "bleeding"
    return re.sub(r"[^\w\s]", " ", t).strip()


_STOP = set("i me my we you he she it they to the a an is are was am of in on at and or for with want wants need needs please can could do does did "
            "ko ka ki ke hai hain ho raha rahi rahe h se me mein ne aur main mujhe hum tum woh wo yeh ye bhi kya kuch nahi nhi nahin pata".split())


def _grams(t: str) -> Counter:
    out: Counter = Counter()
    for w in _norm(t).split():
        if w in _STOP:
            continue
        w = f" {w} "
        for n in (3, 4, 5):
            for i in range(len(w) - n + 1):
                out[zlib.crc32(w[i:i + n].encode('utf-8')) % DIM] += 1  # crc32, NOT hash(): hash() is randomised per process
    return out


class NgramEmbedder:
    name = "ngram"

    def __init__(self, corpus: list[str]):
        df: Counter = Counter()
        for c in corpus:
            df.update(_grams(c).keys())
        n = len(corpus)
        self.idf = {k: math.log((n + 1) / (v + 1)) + 1 for k, v in df.items()}

    def encode(self, texts: list[str]) -> list[dict]:
        out = []
        for t in texts:
            v = {k: (1 + math.log(c)) * self.idf.get(k, 1.0) for k, c in _grams(t).items()}
            z = math.sqrt(sum(x * x for x in v.values())) or 1.0
            out.append({k: x / z for k, x in v.items()})
        return out

    @staticmethod
    def cos(a: dict, b: dict) -> float:
        if len(a) > len(b):
            a, b = b, a
        return sum(x * b.get(k, 0.0) for k, x in a.items())


class E5Embedder:
    name = "e5"

    def __init__(self, model_dir: str):
        from sentence_transformers import SentenceTransformer  # optional dependency

        self.m = SentenceTransformer(model_dir)

    def encode(self, texts: list[str]):
        return self.m.encode([f"query: {t}" for t in texts], normalize_embeddings=True)

    @staticmethod
    def cos(a, b) -> float:
        return float(sum(x * y for x, y in zip(a, b)))


# Similarity alone is not enough: the text must also contain a hallmark word for the flag (typo-tolerant stems), so that
# shared function words / Devanagari suffixes ("हो रही है") or one shared word ("very weak") can never raise a 112 by themselves.
_ANCHORS = {
    "chest_pain": re.compile(r"chest|chet|seene|seena|chhati|chati|heart|hart|\bdil\b|pressure|tight|jalan|pasina|sweat|left arm|jabda|सीने|छाती|दिल|पसीना"),
    "breathlessness": re.compile(r"breat|brea|saans|sans\b|saas|saa?ns|\bair\b|gasp|gaasp|chok|\bdam\b|blue|neele|neela|सांस|साँस|दम"),
    "unconsciousness": re.compile(r"faint|conscious|behosh|hosh|respond|wake|collaps|passed out|pass out|unresp|limp|jawab|aankhen|बेहोश|होश|जवाब"),
    "severe_bleeding": re.compile(r"blood|bleed|blee|khoon|khun|gushing|pouring|wound|ghav|खून|घाव"),
    "stroke_symptoms": re.compile(r"face|chehra|mouth|muh|speech|slur|bol|speak|arm|haath|hand|leg|pair|one side|ek taraf|paraly|lakw|droop|tedha|numb|चेहरा|मुँह|मुह|बोल|हाथ|लकवा|तरफ"),
    "seizure": re.compile(r"seiz|\bfit|fits\b|daura|mirgi|jhaag|jhag|foam|convuls|jerk|jhatke|akad|दौरा|झाग|मिर्गी|झटके"),
    "high_fever_infant": re.compile(r"baby|babe|infant|newborn|bachch|bacch|shishu|month|mahine|mahina|नवजात|बच्च|शिशु|महीन"),
    "suicidal_ideation": re.compile(r"\bdie\b|death|marn|\bmar\b|jeen|jina|suicid|kill|\blife\b|zindagi|jindagi|khatam|end it|मर|जीना|जीने|ज़िंदगी|ज़िन्दगी|आत्म"),
    "severe_dehydration": re.compile(r"no urine|not passed|without urine|peshab nahi|pesab nahi|sunken|dhans|dehydr|can'?t (?:drink|keep)|cannot (?:drink|keep)|पेशाब नहीं|धँस"),
}


@dataclass
class SemanticHit:
    flag: str
    score: float
    margin: float
    matched: str


_NEG = re.compile(r"^(?:no|without)\b|\bno (?:\w+ ){0,2}(?:issue|issues|problem|problems|trouble|pain)\b|\b(?:nahi|nahin|nhi) hai\b|\btheek hai\b|\bbreathing (?:fine|normal|normally)\b|\bsaans theek\b|\bdon'?t have\b|\bdoes ?n'?t have\b")


def _segments(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"[.!?\n;]+|\b(?:and|aur|but|lekin)\b", text) if p.strip()]
    return list(dict.fromkeys([text.strip(), *parts]))


class SemanticSafety:
    def __init__(self, threshold: float = 0.42, margin: float = 0.07, embedder: str | None = None, path: Path = EXEMPLARS):
        spec = json.loads(path.read_text(encoding="utf-8"))
        self.pos = [(f, t) for f, ts in spec["positive"].items() for t in ts]
        self.neg = list(spec["negative"])
        self.threshold, self.margin = threshold, margin
        kind = (embedder or os.getenv("SEMANTIC_EMBEDDER", "ngram")).lower()
        corpus = [t for _, t in self.pos] + self.neg
        if kind == "e5":
            self.emb = E5Embedder(os.environ["SEMANTIC_MODEL_DIR"])
            self.threshold = float(os.getenv("SEMANTIC_THRESHOLD", "0.86"))
            self.margin = float(os.getenv("SEMANTIC_MARGIN", "0.02"))
        else:
            self.emb = NgramEmbedder(corpus)
        self.pv = self.emb.encode([t for _, t in self.pos])
        self.nv = self.emb.encode(self.neg)

    def check(self, text: str) -> SemanticHit | None:
        best: SemanticHit | None = None
        for seg in _segments(text):
            if _NEG.search(_norm(seg)):
                continue  # "no breathing problem": counter-examples cover the rest
            v = self.emb.encode([seg])[0]
            neg = max((self.emb.cos(v, n) for n in self.nv), default=0.0)
            for (flag, ex), p in zip(self.pos, self.pv):
                s = self.emb.cos(v, p)
                anchor = _ANCHORS.get(flag)
                if anchor and not anchor.search(_norm(seg)):
                    continue
                if s >= self.threshold and s - neg >= self.margin and (best is None or s > best.score):
                    best = SemanticHit(flag, round(s, 3), round(s - neg, 3), ex)
        return best


@lru_cache
def get_semantic_safety() -> SemanticSafety | None:
    if os.getenv("SEMANTIC_SAFETY", "on").lower() in ("off", "0", "false"):
        return None
    try:
        return SemanticSafety()
    except Exception:  # never let the optional net break the deterministic floor
        return None
