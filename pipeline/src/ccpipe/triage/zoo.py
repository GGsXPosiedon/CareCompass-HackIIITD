"""Candidate pipelines. Every vectoriser is fit on the training fold only (sklearn Pipeline)."""
from __future__ import annotations

from sklearn.naive_bayes import ComplementNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC

from .features import ConceptFeatures, Lower, RomanView, tfidf_char, tfidf_word

FEATURE_SETS = {
    "raw_char": ("raw",),
    "roman_char": ("roman",),
    "raw+roman_char": ("raw", "roman"),
    "raw+roman+words": ("raw", "roman", "words"),
    "text+concepts*": ("raw", "roman", "words", "concepts"),
    "concepts_only*": ("concepts",),
}
CLASSIFIERS = {
    "lr_c1": lambda: LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000),
    "lr_c10": lambda: LogisticRegression(C=10.0, class_weight="balanced", max_iter=2000),
    "svm_c1": lambda: LinearSVC(C=1.0, class_weight="balanced"),
    "cnb": lambda: ComplementNB(alpha=0.3),
    "1nn": lambda: KNeighborsClassifier(n_neighbors=1, metric="cosine"),
}


def _branch(kind: str):
    if kind == "raw":
        return Pipeline([("lower", Lower()), ("v", tfidf_char())])
    if kind == "roman":
        return Pipeline([("roman", RomanView()), ("v", tfidf_char())])
    if kind == "words":
        return Pipeline([("roman", RomanView()), ("v", tfidf_word())])
    if kind == "concepts":
        return ConceptFeatures()
    raise KeyError(kind)


def build(feature_set: str, clf: str) -> Pipeline:
    union = FeatureUnion([(k, _branch(k)) for k in FEATURE_SETS[feature_set]])
    return Pipeline([("features", union), ("clf", CLASSIFIERS[clf]())])


def all_configs() -> list[tuple[str, str]]:
    return [(f, c) for f in FEATURE_SETS for c in CLASSIFIERS]
