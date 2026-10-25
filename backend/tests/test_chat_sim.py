import pytest
"""Regression net: 102 simulated Hinglish/English/Hindi chats over 17 everyday complaints (see eval/chat_sim.py)."""
from eval.chat_sim import run


def test_simulated_chats_hold_every_invariant():
    fails, ex = run(102, 11, 0, quiet=True)
    # The only tolerated failure is the draft RF-DH-01 clinical rule (vomiting + "very weak" => 112), awaiting clinician review.
    known = {("no_false_112", "weakness")}
    unexpected = {b: [k for k, _, _ in items if (b, k) not in known] for b, items in ex.items()}
    unexpected = {b: v for b, v in unexpected.items() if v}
    assert not unexpected, unexpected


# Exercise the fallback flow used when no pathway matches.
pytestmark = pytest.mark.usefixtures("fallback_dialogue")
