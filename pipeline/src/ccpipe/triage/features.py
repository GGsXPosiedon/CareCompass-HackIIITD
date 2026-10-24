"""Feature engineering for text -> care_type. Only the utterance is used (never lat/lng, never ids).

Views of the same text:
  raw      lowercased NFC text (char_wb 2-5 grams catch spelling variants inside a script)
  roman    Devanagari transliterated to Latin and phonetically folded, so "बुखार", "bukhar", "bukhaar"
           share n-grams across scripts
  concepts Stage-4 extractor facts (present/absent/... per concept) + experiencer + duration
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

import numpy as np
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate
from scipy import sparse
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer

from ..extraction.extractor import extract
from ..extraction.registry import load_registry

_DEVA = re.compile(r"[ऀ-ॿ]")
EXPERIENCERS = ["unspecified", "self", "other_unspecified", "father", "mother", "wife", "husband",
                "grandmother", "grandfather", "child", "sibling", "multiple"]
ASSERTIONS = ["present", "absent", "historical", "hypothetical", "conflicting"]


_VOWELS = "aeiouAIU"


def _deva_word_to_roman(word: str) -> str:
    """Transliterate one Devanagari word and apply Hindi schwa deletion (final and medial)."""
    w = transliterate(word, sanscript.DEVANAGARI, sanscript.ITRANS)
    w = w.replace(".N", "").replace(".n", "")
    w = re.sub(r"M$", "", w).replace("M", "n").replace("~N", "n").replace("N", "n")
    if len(w) > 2 and w.endswith("a") and w[-2] not in _VOWELS:
        w = w[:-1]
    w = re.sub(r"(?<=[^%s])a(?=[^%s][%s])" % (_VOWELS, _VOWELS, _VOWELS), "", w) if len(w) > 4 else w
    return w.lower()


@lru_cache(maxsize=None)
def to_roman(text: str) -> str:
    """Devanagari -> Latin with schwa deletion, then fold Hinglish spelling variation. Idempotent on Latin."""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\u0900-\u097f]+", lambda m: _deva_word_to_roman(m.group()), text).lower()
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = text.replace("w", "v").replace("z", "j")
    text = re.sub(r"(.)\1+", r"\1", text)                    # bukkhar/aa/ee -> single letters
    text = re.sub(r"([bcdfgjklmnpqrstvxy])h", r"\1", text)    # kh->k, th->t, dh->d, bh->b, gh->g ...
    text = re.sub(r"[nm](?=[bcdfgjklpqrstvxy])", "", text)     # nasals before consonants (khansi ~ khasi)
    text = re.sub(r"ni\b", "ni", text)
    return re.sub(r"\s+", " ", text).strip()


class RomanView(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return [to_roman(t) for t in X]


_CONCEPT_CACHE: dict[str, np.ndarray] = {}


class ConceptFeatures(BaseEstimator, TransformerMixin):
    """Dense features from the rule extractor. NOTE: the registry was authored while reading the CareCompass
    utterances, so CV scores that include this block are optimistic (reported as such)."""

    def fit(self, X, y=None):
        reg = load_registry()
        self.concepts_ = sorted(reg.concepts)
        return self

    def transform(self, X):
        return sparse.csr_matrix(np.vstack([self._vec(t) for t in X]))

    def _vec(self, text):
        cached = _CONCEPT_CACHE.get(text)
        if cached is None:
            res = extract(text)
            vec = np.zeros(len(self.concepts_) * len(ASSERTIONS) + len(EXPERIENCERS) + 2)
            for f in res.facts:
                cid = f.concept_id[3:]
                vec[self.concepts_.index(cid) * len(ASSERTIONS) + ASSERTIONS.index(f.assertion.value)] = 1.0
            off = len(self.concepts_) * len(ASSERTIONS)
            vec[off + EXPERIENCERS.index(res.experiencer if res.experiencer in EXPERIENCERS else "unspecified")] = 1.0
            vec[-2] = float(res.needs_clarification)
            vec[-1] = 0.0 if res.duration is None or res.duration.days is None else min(res.duration.days, 14) / 14
            cached = _CONCEPT_CACHE[text] = vec
        return cached


class Lower(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return [unicodedata.normalize("NFC", t).lower() for t in X]


def tfidf_char(lo=2, hi=5):
    return TfidfVectorizer(analyzer="char_wb", ngram_range=(lo, hi), sublinear_tf=True, min_df=1)


def tfidf_word(hi=2):
    return TfidfVectorizer(analyzer="word", ngram_range=(1, hi), sublinear_tf=True, token_pattern=r"(?u)[\wऀ-ॿ']+")
