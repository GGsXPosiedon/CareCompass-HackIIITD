"""Trained heads on top of the multilingual-e5 sentence encoder (care type + emergency score).

Artifact: app/models/router_e5_lr.json, written by pipeline/scripts/export_router.py from the leave-one-family-out study in
pipeline/reports/08_embed_router.md. Runtime needs `onnxruntime tokenizers numpy` and the downloaded model folder
(ENCODER_PATH, e.g. pipeline/models/multilingual-e5-base). Anything missing => `EncoderModels.maybe()` returns None and the
rules / LLM stay in charge exactly as before.

The emergency score can only RAISE caution (ask a danger-sign question, or send to 112 at a very high score); it never lowers
a rules or LLM decision.
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("carecompass.encoder")
ARTIFACT = Path(__file__).resolve().parents[1] / "models" / "router_e5_lr.json"
ASK_FOLLOWUP = "ask_followup"


@dataclass(frozen=True)
class Scores:
    probs: dict          # class -> probability (care types + ask_followup)
    emergency: float     # P(emergency) from the binary head


def _softmax(z: list[float]) -> list[float]:
    m = max(z)
    e = [math.exp(v - m) for v in z]
    s = sum(e)
    return [v / s for v in e]


class EncoderModels:
    def __init__(self, embedder, artifact: dict):
        self.embedder, self.art = embedder, artifact
        self.tau_ask = float(os.getenv("EMERGENCY_TAU_ASK", artifact["tau_ask"]))
        self.tau_emergency = float(os.getenv("EMERGENCY_TAU_ESCALATE", artifact["tau_emergency"]))
        self.tau_margin = float(os.getenv("AMBIGUITY_TAU_MARGIN", artifact.get("tau_margin", 0.0)))  # 0 = never ask
        self.version = artifact["version"]

    @classmethod
    def maybe(cls, encoder_path: str | None) -> "EncoderModels | None":
        path = (encoder_path or "").strip()
        if not path:
            return None
        try:
            from .onnx_embed import OnnxEmbedder

            art = json.loads(ARTIFACT.read_text(encoding="utf-8"))
            models = cls(OnnxEmbedder(path), art)
            log.info("encoder heads enabled: %s (%s)", path, models.version)
            return models
        except Exception as exc:
            log.warning("encoder heads disabled (%s); rules/LLM only", exc)
            return None

    @lru_cache(maxsize=512)
    def _scores(self, text: str) -> Scores:
        v = self.embedder.encode([text[:600]])[0].tolist()
        a = self.art
        z = [sum(w * x for w, x in zip(row, v)) + b for row, b in zip(a["coef"], a["intercept"])]
        probs = dict(zip(a["classes"], _softmax(z)))
        e = a["emergency"]
        ze = sum(w * ((x - m) / (s or 1.0)) for w, x, m, s in zip(e["coef"], v, e["mean"], e["scale"])) + e["intercept"]
        return Scores(probs, 1.0 / (1.0 + math.exp(-ze)))

    def scores(self, text: str) -> Scores:
        return self._scores(" ".join(text.split()))

    def emergency_score(self, latest: str, whole: str = "") -> float:
        """Highest of: the latest message alone and the whole user side of the conversation."""
        s = self.scores(latest).emergency
        if whole and whole != latest:
            s = max(s, self.scores(whole).emergency)
        return s
