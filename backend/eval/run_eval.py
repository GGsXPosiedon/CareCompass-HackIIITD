"""Offline evaluation against the hackathon judging questions.

    python -m eval.run_eval                      # our hand-labelled gold set, current config (LLM on if key set)
    python -m eval.run_eval --file other.jsonl   # any file in the same shape (or the organiser's nested shape)
    python -m eval.run_eval --llm off            # force the deterministic path

Metrics
  1. Emergency recall (MUST be 1.0) and false-alarm rate        -> "Is it safe?"
  2. Care-type and urgency accuracy, per language                -> "understands messy Hindi/Hinglish?"
  3. Follow-up: asked when it should / not when it shouldn't     -> "knows when to ask"
  4. Caregiver pick validity (role, skill, radius, free, language) for our matcher vs the organiser baseline
  5. Explainability: every decision carries plain-language reasoning; every caregiver a reason
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import ROLE_BY_CARE_TYPE, get_settings  # noqa: E402
from app.db.repository import CaregiverRepository  # noqa: E402
from app.schemas.external import TriageRequest  # noqa: E402
from app.services import intake  # noqa: E402
from app.services.gemini import GeminiClient  # noqa: E402
from app.services.lexicon import REQUIRED_SKILLS  # noqa: E402
from app.services.matching import Matcher, haversine_km  # noqa: E402
from app.services.pipeline import Pipeline  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
BASELINE_W = {"language": 0.35, "proximity": 0.30, "skill": 0.20, "rating": 0.15}


def load(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "expected" not in r and "response" in r:  # organiser nested shape
            req, resp = r.get("request", r), r["response"]
            r = {"id": r.get("id"), "language": (r.get("detected_language") or "auto").lower(), **req,
                 "expected": {"care_type": resp.get("care_type"), "urgency": resp.get("urgency"),
                              "red_flags": resp.get("red_flags", []), "follow_up": bool(resp.get("follow_up_question"))}}
        rows.append(r)
    return rows


def wants_language(lang: str, cg) -> bool:
    return ("English" in cg.languages) if lang == "en" else ("Hindi" in cg.languages)


def pick_checks(matcher: Matcher, ids: list[str], care_type: str, urgency: str, facts, loc) -> dict:
    """Validity of a list of picks against the judging criteria."""
    need = [g for c in facts.concepts if facts.present(c) for g in REQUIRED_SKILLS.get(c, [])]
    if care_type == "teleconsultation":
        need = [{"teleconsultation"}]
    elif care_type == "lab_test_home":
        need = [{"sample_collection", "home_phlebotomy"}]
    out = defaultdict(int)
    for cid in ids:
        cg = matcher.repo.get(cid)
        out["n"] += 1
        out["role_ok"] += cg.role == ROLE_BY_CARE_TYPE[care_type] and cg.active
        out["skill_ok"] += all(g & cg.skills for g in need)
        out["free_ok"] += matcher._availability(cg, urgency) is not None
        out["radius_ok"] += care_type == "teleconsultation" or loc is None or haversine_km(loc.lat, loc.lng, cg.lat, cg.lng) <= cg.max_radius_km
        out["language_ok"] += wants_language(facts.language, cg)
    return out


def baseline_picks(matcher: Matcher, care_type: str, facts, loc) -> list[str]:
    """Organiser reference recipe: language .35, proximity .30, skill .20, rating .15; no availability / required-skill filter."""
    scored = []
    for cg in matcher.repo.all():
        if not cg.active or cg.role != ROLE_BY_CARE_TYPE[care_type]:
            continue
        dist = None if care_type == "teleconsultation" or loc is None else haversine_km(loc.lat, loc.lng, cg.lat, cg.lng)
        if dist is not None and dist > cg.max_radius_km:
            continue
        lang = 1.0 if wants_language(facts.language, cg) else 0.0
        hints = {s for c in facts.concepts if facts.present(c) for g in REQUIRED_SKILLS.get(c, []) for s in g}
        skill = len(hints & cg.skills) / len(hints) if hints else 1.0
        comps = {"language": lang, "skill": skill, "rating": cg.rating / 5}
        w = {k: BASELINE_W[k] for k in comps}
        if dist is not None:
            comps["proximity"] = max(0.0, 1 - dist / cg.max_radius_km)
            w["proximity"] = BASELINE_W["proximity"]
        scored.append((sum(comps[k] * w[k] for k in comps) / sum(w.values()), cg.caregiver_id))
    return [cid for _, cid in sorted(scored, key=lambda x: (-x[0], x[1]))[:3]]


def pct(a: float, b: float) -> str:
    return "n/a" if not b else f"{100 * a / b:.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(Path(__file__).with_name("gold_cases.jsonl")))
    ap.add_argument("--llm", choices=["auto", "off"], default="auto")
    ap.add_argument("--now", default="2026-10-24T12:00", help="fixed clock (IST) for availability, for reproducible runs")
    ap.add_argument("--out", default=str(Path(__file__).with_name("report.md")))
    args = ap.parse_args()

    s = get_settings()
    if args.llm == "off":
        s = dataclasses.replace(s, gemini_api_key="")
    now = datetime.fromisoformat(args.now).replace(tzinfo=IST)
    repo = CaregiverRepository(s.caregivers_path)
    matcher = Matcher(repo, s, now_fn=lambda: now)
    pipe = Pipeline(settings=s, repo=repo, matcher=matcher, llm=GeminiClient(s))
    mode = f"LLM={pipe.llm.model}" if pipe.llm.enabled else "LLM off (rules only)"

    rows = load(Path(args.file))
    tally = defaultdict(int)
    by_lang = defaultdict(lambda: defaultdict(int))
    ours, base = defaultdict(int), defaultdict(int)
    failures, latencies = [], []
    for r in rows:
        exp = r["expected"]
        req = TriageRequest(**{k: r[k] for k in ("user_input", "conversation_history", "location") if k in r},
                            language=r.get("language", "auto") if r.get("language") in ("en", "hi", "hinglish", "auto") else "auto")
        t0 = time.perf_counter()
        resp = pipe.triage(req)
        latencies.append(time.perf_counter() - t0)
        facts = intake.build_facts(req)
        lang = r.get("language", facts.language)
        gold_em, pred_em = exp["care_type"] == "emergency_112", resp.care_type == "emergency_112"
        tally["n"] += 1
        if gold_em:
            tally["em_gold"] += 1
            tally["em_hit"] += pred_em
            tally["flag_hit"] += pred_em and bool(set(exp["red_flags"]) & set(resp.red_flags))
        else:
            tally["nonem_gold"] += 1
            tally["false_alarm"] += pred_em
        if exp["follow_up"]:
            tally["ask_gold"] += 1
            tally["ask_hit"] += bool(resp.follow_up_question)
        else:
            tally["noask_gold"] += 1
            tally["needless_ask"] += bool(resp.follow_up_question)
        if exp["care_type"]:
            tally["ct_gold"] += 1
            ok_ct = resp.care_type == exp["care_type"]
            tally["ct_hit"] += ok_ct
            tally["urg_hit"] += resp.urgency == exp["urgency"]
            by_lang[lang]["n"] += 1
            by_lang[lang]["hit"] += ok_ct
            if not ok_ct:
                failures.append((r["id"], lang, r["user_input"], exp["care_type"], resp.care_type or f"ask: {resp.follow_up_question}"))
        elif not resp.follow_up_question:
            failures.append((r["id"], lang, r["user_input"], "follow-up", resp.care_type))
        tally["explained"] += bool(resp.reasoning or resp.follow_up_question)
        tally["cg_reasons"] += all(c.reason for c in resp.matched_caregivers)
        if resp.care_type and resp.care_type != "emergency_112":
            loc = req.location
            for k, v in pick_checks(matcher, [c.caregiver_id for c in resp.matched_caregivers], resp.care_type, resp.urgency, facts, loc).items():
                ours[k] += v
            for k, v in pick_checks(matcher, baseline_picks(matcher, resp.care_type, facts, loc), resp.care_type, resp.urgency, facts, loc).items():
                base[k] += v
            tally["routed"] += 1
            tally["routed_empty"] += not resp.matched_caregivers

    em_recall = tally["em_hit"] / max(1, tally["em_gold"])
    lines = [
        "# CareCompass evaluation report", "",
        f"- Data: `{Path(args.file).name}` ({tally['n']} cases) · Mode: **{mode}** · Clock: {args.now} IST",
        f"- Median latency: {sorted(latencies)[len(latencies) // 2] * 1000:.0f} ms", "",
        "## 1. Safety (never miss an emergency)", "",
        "| Metric | Value | Target |", "|---|---|---|",
        f"| Emergency recall | **{pct(tally['em_hit'], tally['em_gold'])}** ({tally['em_hit']}/{tally['em_gold']}) | 100% |",
        f"| Correct red-flag named (of caught) | {pct(tally['flag_hit'], tally['em_hit'])} | high |",
        f"| False-alarm rate (non-emergency sent to 112) | {pct(tally['false_alarm'], tally['nonem_gold'])} | low, but acceptable |", "",
        "## 2. Care type and urgency", "",
        "| Metric | Value |", "|---|---|",
        f"| Care-type accuracy | {pct(tally['ct_hit'], tally['ct_gold'])} ({tally['ct_hit']}/{tally['ct_gold']}) |",
        f"| Urgency accuracy | {pct(tally['urg_hit'], tally['ct_gold'])} |",
        *[f"| Care-type accuracy · {k} | {pct(v['hit'], v['n'])} ({v['hit']}/{v['n']}) |" for k, v in sorted(by_lang.items())], "",
        "## 3. Knows when to ask", "",
        "| Metric | Value |", "|---|---|",
        f"| Asked on vague input | {pct(tally['ask_hit'], tally['ask_gold'])} ({tally['ask_hit']}/{tally['ask_gold']}) |",
        f"| Needless question on clear input | {pct(tally['needless_ask'], tally['noask_gold'])} |", "",
        "## 4. Caregiver picks (top-3) vs organiser baseline", "",
        "| Check | Ours | Baseline recipe |", "|---|---|---|",
        *[f"| {label} | {pct(ours[k], ours['n'])} | {pct(base[k], base['n'])} |" for k, label in [
            ("role_ok", "Right role & active"), ("skill_ok", "Has the required skill"), ("free_ok", "Free in the needed window"),
            ("radius_ok", "Within service radius"), ("language_ok", "Speaks the family's language")]],
        f"| Routed cases with no eligible caregiver | {pct(tally['routed_empty'], tally['routed'])} | – |", "",
        "## 5. Explainability", "",
        f"- Decisions with plain-language reasoning or a question: {pct(tally['explained'], tally['n'])}",
        f"- Responses where every caregiver has a reason: {pct(tally['cg_reasons'], tally['n'])}", "",
        "## Misses", "",
        *([f"- `{i}` [{l}] {t!r}: expected **{e}**, got **{g}**" for i, l, t, e, g in failures] or ["- none"]),
    ]
    report = "\n".join(lines)
    Path(args.out).write_text(report + "\n", encoding="utf-8")
    print(report)
    return 0 if em_recall == 1.0 else 1  # CI gate: any missed emergency fails the run


if __name__ == "__main__":
    raise SystemExit(main())
