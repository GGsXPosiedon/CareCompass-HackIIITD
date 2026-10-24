"""Graph nodes. Every node is small, pure-ish and logs a plain-language trace entry.

Safety contract (enforced here, tested in tests/):
  1. The deterministic rule engine runs first; if it fires, no model is consulted and the answer is 112.
  2. Any model (LLM safety screener, LLM triage, or the deterministic classifier) can ESCALATE to 112.
     Nothing can de-escalate a rules emergency.
  3. A 'possible' red flag is never silently dropped: we ask one danger-sign question, or escalate if the
     question budget is used up.
  4. Emergencies never carry caregivers; follow-ups never carry a decision (TriageResponse validator).
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from ..config import RED_FLAGS
from ..prompts import load, render_case
from ..schemas.external import MatchedCaregiver, TriageResponse
from ..schemas.internal import RouteDecision, SafetyResult
from ..schemas.llm import SafetyReview, TriageAssessment
from ..services import explain, follow_up, intake
from ..services.gemini import LLMError
from ..services.lexicon import REQUIRED_SKILLS
from ..services.routing import urgency_for
from .state import TriageState

if TYPE_CHECKING:
    from ..services.pipeline import Pipeline

log = logging.getLogger("carecompass.graph")
SAFETY_PROMPT = "safety_screener"
TRIAGE_PROMPT = "triage_analyst"


def _t(node: str, detail: str, **data: Any) -> dict:
    return {"trace": [{"node": node, "detail": detail, **({"data": data} if data else {})}]}


class Nodes:
    def __init__(self, pipe: "Pipeline"):
        self.p = pipe

    # -- 1. intake ---------------------------------------------------------
    def intake(self, s: TriageState) -> dict:
        facts = intake.build_facts(s["request"])
        found = [c for c in facts.concepts if facts.present(c)]
        return {"facts": facts, **_t("intake", f"language={facts.language}; follow-ups asked={facts.n_follow_ups_asked}; concepts={found}")}

    # -- 2. deterministic red-flag rules -------------------------------------
    def rules_safety(self, s: TriageState) -> dict:
        r = self.p.safety.evaluate(s["facts"])
        msg = f"rules fired {r.rule_ids} -> {r.flags}" if r.requires_emergency else "no red-flag rule fired"
        return {"rule_safety": r, **_t("rules_safety", f"{msg} (ruleset {r.ruleset_version})")}

    @staticmethod
    def after_rules(s: TriageState) -> list[str] | str:
        if s["rule_safety"].requires_emergency:
            return "emergency"
        return ["classify", "llm_safety", "llm_triage"]  # parallel fan-out

    # -- 3a. deterministic classifier slot ---------------------------------
    def classify(self, s: TriageState) -> dict:
        d = self.p.router.predict(s["facts"])
        return {"det": d, **_t("classify", f"{self.p.router.name}: {d.care_type} (conf {d.confidence:.2f}) evidence={d.evidence}")}

    # -- 3b/3c. LLM nodes ----------------------------------------------------
    def _case(self, s: TriageState) -> str:
        f = s["facts"]
        return render_case(language=f.language, history=f.history, message=f.latest_input,
                           profile=f.patient_context, follow_ups_asked=f.n_follow_ups_asked)

    def llm_safety(self, s: TriageState) -> dict:
        if not self.p.llm or not self.p.llm.enabled:
            return {"llm_safety": None, **_t("llm_safety", "skipped (LLM off)")}
        pr = load(SAFETY_PROMPT)
        try:
            out = self.p.llm.structured(pr.text, self._case(s), SafetyReview, max_tokens=600)
            return {"llm_safety": out, **_t("llm_safety", f"{pr.tag}: " + (", ".join(f"{x.flag}:{x.status}" for x in out.findings) or "no findings"))}
        except LLMError as e:
            log.warning("llm_safety failed: %s", e)
            return {"llm_safety": None, **_t("llm_safety", f"{pr.tag} failed ({e}); rules remain the safety floor")}

    def llm_triage(self, s: TriageState) -> dict:
        if not self.p.llm or not self.p.llm.enabled:
            return {"llm_triage": None, **_t("llm_triage", "skipped (LLM off)")}
        pr = load(TRIAGE_PROMPT)
        try:
            out = self.p.llm.structured(pr.text, self._case(s), TriageAssessment)
            return {"llm_triage": out, **_t("llm_triage", f"{pr.tag}: {out.care_type} ({out.confidence}) flags={out.red_flags}")}
        except LLMError as e:
            log.warning("llm_triage failed: %s", e)
            return {"llm_triage": None, **_t("llm_triage", f"{pr.tag} failed ({e}); using deterministic classifier")}

    # -- 4. fusion + guard ---------------------------------------------------
    def fuse(self, s: TriageState) -> dict:
        f, det = s["facts"], s["det"]
        sr: SafetyReview | None = s.get("llm_safety")
        tr: TriageAssessment | None = s.get("llm_triage")
        st = self.p.settings
        budget_left = f.n_follow_ups_asked < st.max_follow_ups

        present = [x.flag for x in (sr.findings if sr else []) if x.status == "present"]
        possible = [x.flag for x in (sr.findings if sr else []) if x.status == "possible"]
        flags = list(dict.fromkeys([*present, *(tr.red_flags if tr else [])]))
        flags = [x for x in flags if x in RED_FLAGS]

        # Guard: any source may escalate.
        escalators = []
        if flags:
            escalators.append("llm")
        if tr and tr.care_type == "emergency_112":
            escalators.append("llm_triage")
        if det.care_type == "emergency_112":
            escalators.append(det.source)
        if escalators:
            d = {"outcome": "emergency", "flags": flags, "basis": "model_guard", "escalated_by": escalators}
            return {"decision": d, **_t("fuse", f"escalated to 112 by {escalators}; flags={flags}")}

        if possible:
            q = sr.screening_question if sr else None
            if budget_left and q:
                d = {"outcome": "follow_up", "question": q, "options": sr.screening_options or None, "basis": "safety_screen", "possible": possible}
                return {"decision": d, **_t("fuse", f"possible red flag {possible}: asking one danger-sign question")}
            d = {"outcome": "emergency", "flags": possible, "basis": "model_guard", "escalated_by": ["possible_flag_no_budget"]}
            return {"decision": d, **_t("fuse", f"possible red flag {possible} and no question budget left -> 112 as a precaution")}

        llm_ct = tr.care_type if tr else None
        det_ct, det_conf = det.care_type, det.confidence
        trusted_det = det_ct if det_ct and det_conf >= st.model_trust_threshold else None
        policy = st.fusion_policy
        ct, basis = None, None
        if policy == "model_first":
            ct, basis = (trusted_det, "model") if trusted_det else (llm_ct, "llm") if llm_ct else (det_ct, "model") if det_ct else (None, None)
        elif policy == "agree_or_ask":
            if llm_ct and det_ct and llm_ct != det_ct and budget_left:
                ct, basis = None, None
            else:
                ct, basis = (llm_ct, "llm") if llm_ct else (det_ct, "model") if det_ct else (None, None)
        else:  # llm_first (default while no trained model exists)
            if tr is not None:
                ct, basis = (llm_ct, "llm") if llm_ct else (trusted_det, "model") if trusted_det else (None, None)
            else:
                ct, basis = (det_ct, "model") if det_ct else (None, None)
        agreement = None if not (llm_ct and det_ct) else llm_ct == det_ct

        if ct is None:
            if budget_left:
                if tr and tr.follow_up_question:
                    q, opts, src = tr.follow_up_question, tr.answer_options or None, "llm"
                else:
                    q, opts = follow_up.next_question(f)
                    src = "template"
                d = {"outcome": "follow_up", "question": q, "options": opts, "basis": f"ask_{src}"}
                return {"decision": d, **_t("fuse", f"not enough detail -> one follow-up question ({src}); policy={policy}")}
            ct, basis = st.fallback_care_type, "fallback"

        d = {"outcome": "route", "care_type": ct, "basis": basis, "policy": policy, "agreement": agreement,
             "llm": {"care_type": llm_ct, "confidence": tr.confidence if tr else None},
             "model": {"care_type": det_ct, "confidence": round(det_conf, 2), "source": det.source}}
        return {"decision": d, **_t("fuse", f"{ct} via {basis} (policy={policy}, model={det_ct}, llm={llm_ct}, agree={agreement})")}

    @staticmethod
    def after_fuse(s: TriageState) -> str:
        return {"emergency": "emergency", "follow_up": "follow_up", "route": "match"}[s["decision"]["outcome"]]

    # -- 5. terminal builders ---------------------------------------------------
    def emergency(self, s: TriageState) -> dict:
        f = s["facts"]
        rs = s["rule_safety"]
        if rs.requires_emergency:
            safety = rs
        else:
            d = s["decision"]
            safety = SafetyResult(True, d["flags"], ["LLM-ESCALATION"], rs.ruleset_version, source="model_guard")
        resp = TriageResponse(care_type="emergency_112", urgency="emergency", red_flags=list(safety.flags),
                              reasoning=explain.emergency_text(safety, f.language), matched_caregivers=[])
        return {"response": resp, **_t("emergency", f"112 response; flags={safety.flags}; source={safety.source}")}

    def follow_up(self, s: TriageState) -> dict:
        d = s["decision"]
        resp = TriageResponse(follow_up_question=d["question"], reasoning="", answer_options=d.get("options"))
        return {"response": resp, **_t("follow_up", d["basis"])}

    def match(self, s: TriageState) -> dict:
        f, d, req = s["facts"], s["decision"], s["request"]
        tr: TriageAssessment | None = s.get("llm_triage")
        ct = d["care_type"]
        urgency = urgency_for(ct)
        required = [g for c in f.concepts if f.present(c) for g in REQUIRED_SKILLS.get(c, [])]
        if ct == "teleconsultation":
            required = [{"teleconsultation"}]
        elif ct == "lab_test_home" and not any(g == {"sample_collection", "home_phlebotomy"} for g in required):
            required.append({"sample_collection", "home_phlebotomy"})
        elif ct in ("paramedic_home_visit", "home_nursing"):
            required = [g for g in required if not g & {"sample_collection", "home_phlebotomy", "teleconsultation"}]
        hints = set().union(*required) if required else set()
        llm_skills = {k for k in (tr.required_skills if tr else []) if k not in hints}
        if ct in ("paramedic_home_visit", "home_nursing"):
            llm_skills -= {"sample_collection", "home_phlebotomy", "teleconsultation", "prescription", "report_review"}
        relaxed = False
        cands = []
        if llm_skills and ct in ("home_nursing", "paramedic_home_visit"):
            cands = self.p.matcher.match(ct, urgency, required + [llm_skills], hints | llm_skills, f.language, req.location)
        if not cands:
            relaxed = bool(llm_skills)
            cands = self.p.matcher.match(ct, urgency, required, hints | llm_skills, f.language, req.location)
        return {"candidates": cands, **_t("match", f"{len(cands)} eligible; required={[sorted(g) for g in required]} "
                                                    f"preferred={sorted(llm_skills)}{' (relaxed)' if relaxed else ''}",
                                         ranking=[{"id": c.caregiver_id, "score": c.score, **c.components} for c in cands])}

    def respond(self, s: TriageState) -> dict:
        f, d = s["facts"], s["decision"]
        tr: TriageAssessment | None = s.get("llm_triage")
        ct, cands = d["care_type"], s["candidates"]
        if d["basis"] == "llm" and tr and tr.reasoning:
            reasoning = tr.reasoning
            if not cands:
                reasoning += explain.no_match_suffix(f.language)
        else:
            stub = RouteDecision(ct, d["model"]["confidence"], s["det"].evidence, d["basis"])
            reasoning = explain.decision_text(f, stub, ct, fallback=d["basis"] == "fallback", no_match=not cands)
        resp = TriageResponse(
            care_type=ct, urgency=urgency_for(ct), red_flags=[], reasoning=reasoning,
            matched_caregivers=[MatchedCaregiver(caregiver_id=c.caregiver_id, score=c.score, reason=c.reason) for c in cands],
        )
        return {"response": resp, **_t("respond", f"reasoning from {'llm' if d['basis'] == 'llm' else 'template'}")}
