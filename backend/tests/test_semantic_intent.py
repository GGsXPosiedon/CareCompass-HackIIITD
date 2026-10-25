import hashlib

import pytest

np = pytest.importorskip("numpy")

from app.services.semantic_intent import CHAT_PROTOS, HEALTH_PROTOS, SemanticIntent


def fake_embed(texts):
    """Bag-of-words hashing embedder: enough to test the wiring without torch."""
    out = np.zeros((len(texts), 256))
    for i, t in enumerate(texts):
        for w in t.lower().split():
            out[i, int(hashlib.md5(w.encode()).hexdigest(), 16) % 256] += 1
    n = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.where(n == 0, 1, n)


def test_net_separates_prototype_neighbours():
    net = SemanticIntent(fake_embed)
    assert net.is_health(HEALTH_PROTOS[0])
    assert not net.is_health(CHAT_PROTOS[0])


def test_net_disabled_without_env(monkeypatch):
    from app.services import semantic_intent as si

    monkeypatch.delenv("INTENT_ENCODER_PATH", raising=False)
    si.get_semantic_intent.cache_clear()
    assert si.get_semantic_intent() is None
