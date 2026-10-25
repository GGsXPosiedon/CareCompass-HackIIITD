"""Optional meaning-based health-intent net (multilingual encoder). Off unless INTENT_ENCODER_PATH points at a local
sentence-transformers model (e.g. pipeline/models/multilingual-e5-base).

It runs only for messages that the deterministic layers (symptom regexes + condition lexicon + fuzzy + morphology) called
"general". It can only turn a "general" reply into a "health" one (which then asks a question); it never routes, never
lowers an urgency and never speaks to the user. Missing dependencies or a missing model simply disable it.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Callable, Optional

log = logging.getLogger("carecompass.intent")

HEALTH_PROTOS = [
    "I have a serious illness", "my father is sick and needs a doctor", "she has been unwell for days", "I need a nurse at home for my mother",
    "he has a chronic disease and needs care", "mujhe koi bimari hai", "papa ki tabiyat kharab hai", "mummy ko dawai aur nurse chahiye",
    "mujhe ek rog hai jiska ilaj chahiye", "बीमारी का इलाज चाहिए", "मेरी तबीयत ठीक नहीं है", "मुझे डॉक्टर से बात करनी है",
    "my child has a medical condition", "I was diagnosed with a disease", "doctor said I have a rare disorder", "I am on treatment for a long illness",
    "need help after surgery at home", "blood test report came positive", "I feel pain and weakness", "she is pregnant and has a problem",
    "he is taking medicines for a long time", "need a caregiver for an old patient", "mujhe bahut ghabrahat ho rahi hai", "I have a skin problem",
    "my grandmother cannot move and needs care", "I need to see a specialist", "mujhe kuch ho gaya hai", "uski haalat kharab hai",
    "I think I have an infection", "my baby is not feeding properly", "I have been feeling very low and cannot sleep",
]
CHAT_PROTOS = [
    "hello how are you", "what is the weather today", "tell me a joke", "who won the cricket match", "book me a flight to Goa", "help me with my homework",
    "what is the capital of France", "recommend a good movie", "how do I cook rice", "write a poem about the sea", "what time is it", "thank you very much",
    "good morning", "kya haal hai", "aaj mausam kaisa hai", "mujhe pizza chahiye", "gaana sunao", "mera phone kharab ho gaya", "wifi nahi chal raha",
    "how to invest in the stock market", "translate this sentence to Hindi", "what is your name", "bitcoin price today", "tell me about Delhi",
    "my laptop is not working", "I want to buy shoes online", "when is Diwali this year", "who are you", "ok", "bye see you later", "नमस्ते आप कैसे हैं",
]


class SemanticIntent:
    def __init__(self, embed: Callable[[list[str]], "object"], margin: float = 0.015, k: int = 3):
        import numpy as np

        self._np, self._embed, self.margin, self.k = np, embed, margin, k
        self._h = np.asarray(embed(HEALTH_PROTOS))
        self._c = np.asarray(embed(CHAT_PROTOS))

    def score(self, text: str) -> float:
        v = self._np.asarray(self._embed([text]))[0]
        h = self._np.sort(self._h @ v)[-self.k:].mean()
        c = self._np.sort(self._c @ v)[-self.k:].mean()
        return float(h - c)

    def is_health(self, text: str) -> bool:
        return self.score(text) > self.margin


def _sentence_transformer_embedder(path: str) -> Callable[[list[str]], "object"]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(path, device="cpu")
    prefix = "query: " if "e5" in path.lower() else ""
    return lambda texts: model.encode([prefix + t for t in texts], normalize_embeddings=True, batch_size=32)


@lru_cache(maxsize=1)
def get_semantic_intent() -> Optional[SemanticIntent]:
    path = os.getenv("INTENT_ENCODER_PATH", "").strip()
    if not path:
        return None
    try:
        si = SemanticIntent(_sentence_transformer_embedder(path), margin=float(os.getenv("INTENT_ENCODER_MARGIN", "0.015")))
        log.info("semantic intent net enabled: %s", path)
        return si
    except Exception as exc:  # missing torch / model: the deterministic layers still work
        log.warning("semantic intent net disabled (%s)", exc)
        return None
