"""Regression gate for the dialogue intent layer (WP1/WP2).

Probe set: pipeline/eval/intent_probe.jsonl. Named conditions (AIDS/HIV, cancer, TB, ...) written in English,
Hindi, Hinglish or SMS style must be treated as health intent, never as the generic 'general' redirect.
Currently FAILS by design: it is the target the open-vocabulary gate (WP2) has to reach.
"""
from eval.intent_probe import predict, run

TARGET_RECALL = 0.97
MAX_FALSE_HEALTH = 0.03


def test_probe_thresholds():
    res = run()
    assert res["health_recall"] >= TARGET_RECALL, f"missed {len(res['misses'])}: {res['misses'][:8]}"
    assert res["false_health_rate"] <= MAX_FALSE_HEALTH, res["false_health"]


def test_mere_aids_h_is_health():
    assert predict("mere aids h") == "health"
    assert predict("hello") == "greeting"
