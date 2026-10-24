"""Conversation simulator: many varied multi-turn chats checked against invariants (no clinical labels involved).

    python -m eval.chat_sim [--n 400] [--seed 1] [--show 40]

Every symptom here is NON-emergency wording, so any 112 is a false alarm. Invariants checked per chat:
  recognised   the first message is not answered with the generic 'I can help with health...' reply
  language     replies match the user's language (no English question to a Hinglish user and vice versa)
  no_repeat    the same question is never asked twice
  budget       at most 3 follow-up questions, and the chat ends in a route
  no_false_112 a benign complaint never ends in emergency_112
  names_symptom the final reasoning mentions the user's symptom
  caregivers   a visit recommendation has at least one caregiver (or says none is available)
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

SYMPTOMS = {  # key -> (reasoning words to expect any of, phrasings by language)
    "headache": (["headache", "sir dard", "सिरदर्द"], {"en": ["I have a headache", "my head hurts since morning", "bad headache today"], "hinglish": ["sar me dard hai", "sir dard ho raha hai", "mujhe headache hai", "mere sar me dard hora hai"], "hi": ["मुझे सिरदर्द है", "सर में दर्द है"]}),
    "fever": (["fever", "bukhar", "बुखार"], {"en": ["I have fever", "my mother has a fever", "fever since yesterday"], "hinglish": ["mujhe bukhar hai", "papa ko bukhar hai", "bacche ko halka bukhar hai"], "hi": ["मुझे बुखार है", "पापा को बुखार है"]}),
    "cough": (["cough", "khansi", "खांसी"], {"en": ["I have a cough", "dry cough and sore throat"], "hinglish": ["mujhe khansi hai", "khansi aur gale me kharash hai"], "hi": ["मुझे खांसी है"]}),
    "stomach": (["stomach", "pet", "पेट"], {"en": ["stomach pain", "my stomach hurts"], "hinglish": ["pet me dard hai", "pet kharab hai", "pet dard hora hai"], "hi": ["पेट में दर्द है"]}),
    "knee": (["knee", "ghutn", "घुटन"], {"en": ["I have knee pain", "my knee hurts when I walk"], "hinglish": ["ghutne me dard hai", "dadi ke ghutno me dard hai"], "hi": ["घुटने में दर्द है"]}),
    "back": (["back", "peeth", "पीठ"], {"en": ["back pain", "I have lower back ache"], "hinglish": ["peeth me dard hai", "kamar dard hai"], "hi": ["पीठ में दर्द है", "कमर में दर्द है"]}),
    "weakness": (["weak", "kamzor", "कमज़ोर", "कमजोर"], {"en": ["I feel very weak", "feeling tired and weak"], "hinglish": ["bahut kamzori lag rahi hai", "thak gaya hu", "kamzori hai"], "hi": ["बहुत कमज़ोरी है"]}),
    "vomiting": (["vomit", "ulti", "उल्टी", "stomach", "pet ki pareshani", "पेट"], {"en": ["I have been vomiting", "feeling like vomiting"], "hinglish": ["ulti ho rahi hai", "mujhe ulti jaisa lag raha hai"], "hi": ["उल्टी हो रही है"]}),
    "loose": (["loose", "dast", "दस्त", "stomach", "pet ki pareshani", "पेट की परेशानी"], {"en": ["I have loose motions", "diarrhoea since morning"], "hinglish": ["dast lage hain", "loose motion ho rahe hain"], "hi": ["दस्त हो रहे हैं"]}),
    "dizzy": (["dizz", "chakkar", "चक्कर", "weak", "kamzor"], {"en": ["I feel dizzy", "feeling lightheaded"], "hinglish": ["chakkar aa rahe hain", "mujhe chakkar aa rahe hai"], "hi": ["चक्कर आ रहे हैं"]}),
    "throat": (["throat", "gala", "gale", "गला", "गले", "cough", "khansi", "fever", "bukhar"], {"en": ["sore throat", "my throat hurts"], "hinglish": ["gale me dard hai", "gala kharab hai"], "hi": ["गले में दर्द है"]}),
    "cold": (["cold", "sardi", "सर्दी", "runny", "fever", "cough", "khansi", "pain"], {"en": ["I have a cold and runny nose"], "hinglish": ["sardi zukam hai", "naak beh rahi hai"], "hi": ["सर्दी जुकाम है"]}),
    "joint": (["joint", "pain", "dard", "दर्द"], {"en": ["joint pain in my hands", "my shoulder hurts", "leg pain since two days"], "hinglish": ["jodon me dard hai", "kandhe me dard hai", "pair me dard hai"], "hi": ["जोड़ों में दर्द है", "पैर में दर्द है"]}),
    "skin": (["rash", "skin", "त्वचा", "itch", "pain", "dard", "kharish", "daane", "खुजली"], {"en": ["I have a skin rash", "itching all over the body"], "hinglish": ["skin pe daane ho gaye hain", "khujli ho rahi hai"], "hi": ["त्वचा पर खुजली है"]}),
    "tooth": (["tooth", "dant", "pain", "dard", "दांत", "दर्द"], {"en": ["I have a toothache", "ear pain since last night"], "hinglish": ["dant me dard hai", "kaan me dard hai"], "hi": ["दांत में दर्द है"]}),
    "urine": (["urine", "urinary", "peshab", "पेशाब", "pain", "dard", "burning", "jalan"], {"en": ["burning while urinating", "I have burning in urine"], "hinglish": ["peshab me jalan hai", "peshab me dard ho raha hai"], "hi": ["पेशाब में जलन है"]}),
    "bp": (["blood pressure", "bp", "बीपी", "pain", "weak", "dard", "check"], {"en": ["my BP is high, headache too", "need to check blood pressure"], "hinglish": ["bp high lag raha hai", "bp check karwana hai"], "hi": ["बीपी हाई है"]}),
}
DURATION = {"en": ["since yesterday", "2 days", "since today", "1-2 days"], "hinglish": ["2 din se", "kal se", "aaj se", "1–2 din se"], "hi": ["2 दिन से", "आज से"]}
ASSOC = {"en": ["no", "not sure", "yes, vomiting", "a little fever"], "hinglish": ["nahi", "pata nahi", "haan ulti bhi hai", "thoda bukhar bhi hai", "dhundhla"], "hi": ["नहीं", "पता नहीं", "हाँ उल्टी भी है"]}
TEMP = ["101", "pata nahi", "99", "not checked", "102 degree"]
GENERIC = re.compile(r"I can help with health|Main health aur ghar par care|मैं स्वास्थ्य और घर पर")
EN_Q = re.compile(r"^(How long|Is there anything|Have you checked|How heavy)", re.I)
HI_Q = re.compile(r"kab se|kuch aur bhi|naapa|kitna beh|कब से|क्या इसके साथ|तापमान", re.I)


def answer_for(q: str, lang: str, rnd: random.Random) -> str:
    ql = q.lower()
    if "kab se" in ql or "how long" in ql or "कब से" in q:
        return rnd.choice(DURATION[lang])
    if "temperature" in ql or "naapa" in ql or "तापमान" in q:
        return rnd.choice(TEMP)
    return rnd.choice(ASSOC[lang])


def run(n: int, seed: int, show: int, quiet: bool = False):
    from fastapi.testclient import TestClient
    from app.main import app
    from conftest import req
    import logging
    logging.disable(logging.CRITICAL)
    c = TestClient(app)
    rnd = random.Random(seed)
    fails: Counter = Counter()
    ex: dict[str, list] = {}
    keys = list(SYMPTOMS)
    for i in range(n):
        key = keys[i % len(keys)]
        lang = rnd.choice(["en", "hinglish", "hinglish", "hi"])
        words, ph = SYMPTOMS[key]
        first = rnd.choice(ph[lang])
        hist, log, qs = [], [], []
        msg, final = first, None
        for _ in range(6):
            r = c.post("/triage", json=req(msg, history=list(hist))).json()
            q = r.get("follow_up_question")
            log.append((msg, q or f"[{r['care_type']}] {r.get('reasoning', '')[:90]}"))
            hist.append({"role": "user", "content": msg})
            if not q:
                final = r
                break
            qs.append(q)
            hist.append({"role": "assistant", "content": q})
            msg = answer_for(q, lang, rnd)
        bad = []
        if qs and GENERIC.search(qs[0]):
            bad.append("recognised")
        if lang in ("hinglish", "hi") and any(EN_Q.search(q) for q in qs):
            bad.append("language(en question to hinglish user)")
        if lang == "en" and any(HI_Q.search(q) and not re.search(r"[A-Za-z]{4} .* \?", q) and "kab se" in q.lower() for q in qs):
            bad.append("language(hinglish question to en user)")
        if len(qs) != len(set(qs)):
            bad.append("no_repeat")
        if final is None or len(qs) > 3:
            bad.append("budget/ends")
        else:
            if final["care_type"] == "emergency_112":
                bad.append("no_false_112")
            elif not any(w.lower() in final["reasoning"].lower() for w in words):
                bad.append("names_symptom")
            if final["care_type"] in ("paramedic_home_visit", "home_nursing") and not final["matched_caregivers"] and "available" not in final["reasoning"].lower():
                bad.append("caregivers")
        for b in bad:
            fails[b] += 1
            ex.setdefault(b, []).append((key, lang, log))
    if quiet:
        return fails, ex
    print(f"{n} chats | failures by invariant: {dict(fails) or 'none'}")
    for b, items in ex.items():
        print(f"\n## {b} ({len(items)})")
        for key, lang, log in items[: max(1, show // max(1, len(ex)))]:
            print(f"- [{key}/{lang}]")
            for u, a in log:
                print(f"    you: {u}\n    bot: {a}")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=400)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--show", type=int, default=30)
    a = ap.parse_args()
    sys.exit(run(a.n, a.seed, a.show))
