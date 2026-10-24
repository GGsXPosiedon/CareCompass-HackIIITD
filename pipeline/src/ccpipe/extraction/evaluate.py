"""Stage 4 evaluation: fact-level precision/recall on (concept, assertion) pairs."""
from __future__ import annotations

import json
from collections import defaultdict

import pandas as pd
import yaml

from ..families import load_family_table
from ..paths import CONFIG_DIR, PIPELINE_DIR, REPORTS_DIR, data_file
from .extractor import extract
from .registry import load_registry


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


def evaluate_families() -> tuple[dict, list[dict]]:
    gold = yaml.safe_load(open(PIPELINE_DIR / "eval" / "extraction_family_gold.yaml", encoding="utf-8"))
    table = load_family_table(CONFIG_DIR / "scenario_families.yaml")
    always = set(gold["always_allowed"])
    reg = load_registry()
    df = pd.read_csv(data_file("carecompass_csv"), dtype=str, keep_default_na=False)
    per_lang: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    errors, dur_checked, dur_ok = [], 0, 0
    for row in df.drop_duplicates("user_input").to_dict("records"):
        fam = table.family_of(row["user_input"])
        g = gold["families"][fam]
        res = extract(row["user_input"], registry=reg)
        present = {f.concept_id[3:] for f in res.facts if f.assertion.value == "present"}
        other = {f.concept_id[3:] for f in res.facts if f.assertion.value != "present"}
        req, allowed = set(g["required"]), set(g["required"]) | set(g["allowed"]) | always
        tp, fn, fp = len(req & present), len(req - present), len((present - allowed) | other)
        lang = row["detected_language"]
        for k, v in zip(range(3), (tp, fp, fn)):
            per_lang[lang][k] += v
        if fn or fp:
            errors.append({"text": row["user_input"], "family": fam, "missed": sorted(req - present),
                           "unexpected": sorted((present - allowed) | other)})
        if "duration_days" in g:
            dur_checked += 1
            dur_ok += int(res.duration is not None and res.duration.days == g["duration_days"])
        if not req and not res.needs_clarification:
            errors.append({"text": row["user_input"], "family": fam, "note": "follow-up case but extractor was confident"})
    totals = [sum(v[i] for v in per_lang.values()) for i in range(3)]
    summary = {"per_language": {k: dict(zip(("tp", "fp", "fn"), v)) for k, v in per_lang.items()},
               "total": dict(zip(("tp", "fp", "fn"), totals)), "duration": [dur_ok, dur_checked]}
    return summary, errors


def evaluate_adversarial() -> tuple[dict, list[dict]]:
    path = PIPELINE_DIR / "eval" / "extraction_adversarial.jsonl"
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    reg = load_registry()
    by_tag: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    errors, exp_checked, exp_ok, dur_checked, dur_ok, clar_checked, clar_ok = [], 0, 0, 0, 0, 0, 0
    for r in rows:
        res = extract(r["text"], registry=reg)
        pred = {(f.concept_id[3:], f.assertion.value) for f in res.facts}
        gold = {tuple(x) for x in r["facts"]}
        tp, fp, fn = len(pred & gold), len(pred - gold), len(gold - pred)
        key = r["tag"].split("_")[0]
        for k, v in enumerate((tp, fp, fn)):
            by_tag[key][k] += v
            by_tag["ALL"][k] += v
        if fp or fn:
            errors.append({"id": r["id"], "text": r["text"], "tag": r["tag"], "missed": sorted(gold - pred),
                           "unexpected": sorted(pred - gold)})
        if "experiencer" in r:
            exp_checked += 1
            ok = res.experiencer == r["experiencer"]
            exp_ok += ok
            if not ok:
                errors.append({"id": r["id"], "text": r["text"], "experiencer": [r["experiencer"], res.experiencer]})
        if "duration_days" in r:
            dur_checked += 1
            ok = res.duration is not None and res.duration.days == r["duration_days"]
            dur_ok += ok
            if not ok:
                errors.append({"id": r["id"], "text": r["text"], "duration": [r["duration_days"], str(res.duration)]})
        if "needs_clarification" in r:
            clar_checked += 1
            ok = res.needs_clarification == r["needs_clarification"]
            clar_ok += ok
            if not ok:
                errors.append({"id": r["id"], "text": r["text"], "needs_clarification": res.needs_clarification})
    summary = {"by_tag": {k: dict(zip(("tp", "fp", "fn"), v)) for k, v in by_tag.items()},
               "experiencer": [exp_ok, exp_checked], "duration": [dur_ok, dur_checked],
               "clarification": [clar_ok, clar_checked], "n": len(rows)}
    return summary, errors


def _row(name: str, d: dict) -> str:
    p, r, f = _prf(d["tp"], d["fp"], d["fn"])
    return f"| {name} | {d['tp']} | {d['fp']} | {d['fn']} | {p:.2f} | {r:.2f} | {f:.2f} |"


def run_extraction_eval() -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fam, fam_err = evaluate_families()
    adv, adv_err = evaluate_adversarial()
    reg = load_registry()
    head = "| Slice | TP | FP | FN | Precision | Recall | F1 |\n|---|---:|---:|---:|---:|---:|---:|"
    lines = ["# 04 — Multilingual symptom extraction (rule-based)", "",
             f"Registry `{reg.version}` ({reg.review_status}; {len(reg.concepts)} concepts). "
             "No gold label here is clinician-reviewed.", "",
             "## A. CareCompass utterances — IN-SAMPLE (66 unique texts)", "",
             "The registry was written while reading these texts, so this measures cross-language consistency, "
             "not generalisation.", "", head]
    lines += [_row(k, v) for k, v in sorted(fam["per_language"].items())] + [_row("ALL", fam["total"])]
    lines += ["", f"Duration correct: {fam['duration'][0]}/{fam['duration'][1]}.", ""]
    lines += ["## B. Adversarial set — 40 hand-written cases (negation, history, third party, Hinglish, noise)", "",
              "Written by the same author in the same session as the lexicon; some variants (e.g. `nhi`, `breathlessness`) were added while writing it. A smoke test, not an independent benchmark. Cases tagged `oov` list only in-vocabulary concepts in their gold, so their score does not count the missed out-of-vocabulary symptoms (e.g. headache).", "", head]
    lines += [_row(k, v) for k, v in sorted(adv["by_tag"].items())]
    lines += ["", f"Experiencer correct: {adv['experiencer'][0]}/{adv['experiencer'][1]}; "
              f"duration correct: {adv['duration'][0]}/{adv['duration'][1]}; "
              f"clarification flag correct: {adv['clarification'][0]}/{adv['clarification'][1]}.", "",
              "## Failure cases", ""]
    for e in fam_err + adv_err:
        lines.append(f"- `{json.dumps(e, ensure_ascii=False)}`")
    lines += ["", "## Known limits", "",
              "- Vocabulary-bound: unlisted symptoms (e.g. headache, vomiting) are not extracted; the result then sets "
              "`needs_clarification`, it never implies absence.",
              "- No fuzzy matching: misspellings outside the listed variants are missed (see tag `noisy`).",
              "- Negation, history and hypothetical cues are shallow window rules, not a parser.",
              "- Extraction states what the text says; it assigns no care type, urgency or red-flag decision.", ""]
    (REPORTS_DIR / "04_extraction.md").write_text("\n".join(lines), encoding="utf-8")
    return {"families": fam, "adversarial": adv}
