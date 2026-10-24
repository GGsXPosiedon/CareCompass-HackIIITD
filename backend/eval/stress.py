"""Stress test for red-flag recall: held-out phrasings (NOT in the exemplar file) x subjects x typos.

    python -m eval.stress [--threshold 0.4 --margin 0.04] [--show-misses]

Reports, per flag, recall of (a) regex rules only and (b) rules + semantic net, plus false alarms on benign texts
(every non-emergency gold case plus extra benign lines). The phrasings are dev-written, unreviewed, and are a
regression net, not clinical validation.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace as N

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.dialogue import _n  # noqa: E402
from app.services.safety import SafetyEngine  # noqa: E402
from app.services.semantic_safety import SemanticSafety  # noqa: E402

SUBJ = ["", "my friend ", "my father ", "mummy ko ", "dost ko ", "he ", "she ", "mere bhai ko ", "baby ", "patient "]
HELD = {
 "breathlessness": ["has stopped breathing", "is not able to take a breath", "is struggling to breathe and turning blue", "ki saans nahi chal rahi", "ko saans lene mein bahut taklif hai",
                    "ki saans uphar gayi hai", "is gasping", "breathing nahi kar raha", "can hardly get air in", "lips turning blue, no air"],
 "chest_pain": ["has severe pain in the chest", "feels heavy pressure on the chest and sweating", "ke seene mein bahut tez dard hai", "ko heart attack jaisa lag raha hai",
                "has crushing chest discomfort", "ko seene me bhaari pan aur pasina aa raha hai"],
 "unconsciousness": ["fainted and is not waking up", "is lying on the floor not responding", "ko hosh nahi hai", "achanak gir kar behosh ho gaya", "has passed out",
                     "is unresponsive and limp", "ne aankhen nahi kholi, jawab nahi de raha"],
 "severe_bleeding": ["is bleeding heavily from the leg", "has blood pouring from the head wound", "ke sir se bahut khoon beh raha hai", "ka khoon ruk nahi raha",
                     "is vomiting blood", "lost a lot of blood after the accident", "ko ulti me khoon aa raha hai"],
 "stroke_symptoms": ["has a drooping face and slurred speech", "suddenly cannot move one side", "ka chehra tedha ho gaya aur bol nahi pa raha", "ek taraf ka haath pair kaam nahi kar raha achanak",
                     "suddenly can't speak properly and arm is weak"],
 "seizure": ["is having fits and foaming", "is convulsing on the floor", "ko mirgi ka daura pada hai", "ke muh se jhaag aa raha hai aur body akad gayi", "had a seizure just now"],
 "high_fever_infant": ["newborn has high fever and is very sleepy", "ko 2 mahine ka bachcha hai tez bukhar aur doodh nahi pi raha", "is a 1 month old baby burning with fever"],
 "suicidal_ideation": ["says they want to die", "wants to end their life tonight", "kehta hai ki wo marna chahta hai", "ne kaha mujhe jeena nahi hai", "is thinking about killing himself"],
 "severe_dehydration": ["has had vomiting and loose motions all day and has not passed urine", "ko bahut dast aur ulti hai peshab nahi aaya, aankhen dhans gayi", "is very weak, cannot keep water down, no urine"],
}
BENIGN = ["papa ko bukhar hai aur khansi", "need a nurse for blood pressure check at home", "book a blood test at home", "mujhe sir dard hai", "knee pain with mild swelling",
          "hello", "what is the weather", "mummy ko kamzori hai", "can i talk to a doctor about my reports", "cold and runny nose since yesterday", "chhoti si khrons lagi hai",
          "mere dost ki naak se khoon arha h", "mujhe medic nhi chaiye", "I don't have chest pain", "no breathing issue only fever", "dadi ke ghutne mein dard hai", "need physiotherapy at home"]


def typo(t: str, rnd: random.Random) -> str:
    w = t.split()
    i = rnd.randrange(len(w))
    x = w[i]
    if len(x) > 4:
        j = rnd.randrange(1, len(x) - 1)
        x = x[:j] + x[j + 1:] if rnd.random() < .5 else x[:j] + x[j] + x[j:]
    w[i] = x
    return " ".join(w)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=None)
    ap.add_argument("--margin", type=float, default=None)
    ap.add_argument("--show-misses", action="store_true")
    a = ap.parse_args()
    eng = SafetyEngine(semantic=False)
    sem = SemanticSafety(**{k: v for k, v in (("threshold", a.threshold), ("margin", a.margin)) if v is not None})
    rnd = random.Random(7)
    gold = [json.loads(x) for x in (ROOT / "eval" / "gold_cases.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    benign = BENIGN + [g["user_input"] for g in gold if g["expected"]["care_type"] != "emergency_112"]

    def rules(t):
        return eng.evaluate(N(text_norm=_n(t), safety_text_norm=_n(t))).requires_emergency

    def both(t):
        return rules(t) or sem.check(t) is not None

    tot = [0, 0, 0]
    print(f"| flag | n | rules recall | rules+semantic recall |\n|---|---|---|---|")
    misses = []
    for flag, ph in HELD.items():
        texts = [f"{s}{p}".strip() for s in SUBJ for p in ph]
        texts += [typo(t, rnd) for t in texts[::2]]
        r = sum(rules(t) for t in texts)
        b = sum(both(t) for t in texts)
        misses += [(flag, t) for t in texts if not both(t)]
        tot = [tot[0] + len(texts), tot[1] + r, tot[2] + b]
        print(f"| {flag} | {len(texts)} | {r/len(texts):.1%} | {b/len(texts):.1%} |")
    print(f"| **all** | {tot[0]} | {tot[1]/tot[0]:.1%} | {tot[2]/tot[0]:.1%} |")
    fa_r = [t for t in benign if rules(t)]
    fa_b = [t for t in benign if both(t)]
    print(f"\nFalse alarms on {len(benign)} benign texts: rules {len(fa_r)}, rules+semantic {len(fa_b)}")
    for t in fa_b:
        print("  FALSE ALARM:", t, sem.check(t))
    if a.show_misses:
        for f, t in misses[:60]:
            print("  MISS", f, "|", t)


if __name__ == "__main__":
    main()
