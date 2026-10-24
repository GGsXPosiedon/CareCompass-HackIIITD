import json

import pytest

from ccpipe.extraction.extractor import extract
from ccpipe.extraction.registry import RegistryError, load_registry, norm_token, tokenize
from ccpipe.paths import PIPELINE_DIR
from ccpipe.schemas import Assertion


def facts(text):
    return {f.concept_id[3:]: f.assertion.value for f in extract(text).facts}


def test_registry_loads_and_has_no_variant_collisions():
    reg = load_registry()
    assert len(reg.concepts) >= 30 and reg.review_status == "unreviewed"


def test_registry_rejects_collision(monkeypatch):
    from ccpipe.extraction import registry as r
    cfg = {"concepts": {"a": {"category": "symptom", "en": ["fever"]}, "b": {"category": "symptom", "en": ["Fever"]}},
           "relations": {}, "first_person": [], "third_person": [], "version": "x", "review_status": "x"}
    monkeypatch.setattr(r, "load_yaml", lambda name: cfg)
    with pytest.raises(RegistryError):
        r.load_registry()


def test_devanagari_tokens_keep_matras_and_offsets():
    text = "पापा को बुखार है।"
    toks = tokenize(text)
    assert [t for t, _, _ in toks] == ["पापा", "को", "बुखार", "है"]
    assert all(text[s:e] for _, s, e in toks)
    assert norm_token("साँस") == norm_token("सांस")


def test_negation_and_unknown_not_absent():
    assert facts("No fever, but cough since yesterday") == {"fever": "absent", "cough": "present"}
    res = extract("severe itching and sneezing since morning")
    assert res.facts == [] and res.needs_clarification  # unlisted symptoms are NOT reported as absent


def test_hindi_negation_vs_persistence():
    assert facts("बुखार नहीं है लेकिन खांसी है") == {"fever": "absent", "cough": "present"}
    assert facts("khansi nahi ruk rahi") == {"cough": "present"}


def test_idiom_negation_is_a_symptom():
    assert facts("saans nahi aa rahi")["breathlessness"] == "present"
    assert facts("He cannot breathe")["breathlessness"] == "present"
    assert facts("no chest pain or breathlessness") == {"chest_pain": "absent", "breathlessness": "absent"}


def test_conflict_history_hypothetical():
    assert facts("No fever. Fever since morning.") == {"fever": "conflicting"}
    assert facts("History of chest pain")["chest_pain"] == "historical"
    assert facts("If the fever continues, I will need a doctor")["fever"] == "hypothetical"


def test_experiencer_and_duration():
    res = extract("My father has had fever and cough for 2 days")
    assert res.experiencer == "father" and res.duration.days == 2
    assert extract("Hi, is anyone there?").needs_clarification


def test_generic_only_needs_clarification():
    assert extract("Doctor chahiye").needs_clarification
    assert not extract("fever hai").needs_clarification


def test_empty_and_garbage_do_not_crash():
    for text in ["", "   ", "?!", "😀", "a" * 5000]:
        res = extract(text)
        assert res.needs_clarification


def test_extractor_only_emits_present_family_facts_with_rule_origin():
    for f in extract("fever and cough").facts:
        assert f.origin.value == "extracted_rule" and f.assertion is Assertion.PRESENT


def test_adversarial_gold_has_no_unexpected_false_positives():
    rows = [json.loads(l) for l in open(PIPELINE_DIR / "eval" / "extraction_adversarial.jsonl", encoding="utf-8")]
    for r in rows:
        pred = {(f.concept_id[3:], f.assertion.value) for f in extract(r["text"]).facts}
        assert not (pred - {tuple(x) for x in r["facts"]}), (r["id"], pred)
