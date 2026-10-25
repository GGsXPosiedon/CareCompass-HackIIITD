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
from ..services import delhi, dialogue, explain, follow_up, intake, intent_llm, mood, pathways
from ..services.conditions import NON_HEALTH_TASK
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
        f = s["facts"]
        r = self.p.safety.evaluate(f)
        a = f.analysis
        extra = ""
        es = None
        if not r.requires_emergency and a is not None and a.danger_answer == "yes":
            # the user confirmed the danger-sign question we asked: that is an emergency, whatever else was said
            r = SafetyResult(True, [], ["DANGER-CONFIRMED"], r.ruleset_version, "rules")
            extra = "; user confirmed the danger-sign question"
        enc = getattr(self.p, "encoder", None)
        if enc is not None and not r.requires_emergency and (a is None or a.act in ("health", "answer")):
            es = enc.emergency_score(f.latest_input or f.text_norm, f.safety_text_norm or f.text_norm)
            extra += f"; emergency score {es:.2f} (ask>={enc.tau_ask}, escalate>={enc.tau_emergency})"
            if es >= enc.tau_emergency:
                r = SafetyResult(True, [], ["ENC-EMERGENCY"], r.ruleset_version, "model_guard")
        msg = f"rules fired {r.rule_ids} -> {r.flags}" if r.requires_emergency else "no red-flag rule fired"
        return {"rule_safety": r, "emergency_score": es, **_t("rules_safety", f"{msg} (ruleset {r.ruleset_version}){extra}")}

    @staticmethod
    def after_rules(s: TriageState) -> str:
        return "emergency" if s["rule_safety"].requires_emergency else "converse"

    # -- 2b. intent + dialogue management (only reached when no red-flag rule fired) ----------------
    def converse(self, s: TriageState) -> dict:
        a = s["facts"].analysis
        d = dialogue.decide(a, self.p.settings.max_follow_ups, self.p.settings.adaptive_slot_questions)
        widened = ""
        if a.act == "general" and d.kind == "reply" and self.p.llm and not NON_HEALTH_TASK.search(s["facts"].latest_input or ""):
            verdict = intent_llm.looks_health_request(self._llm("triage"), s["facts"].latest_input or "")
            if verdict:
                a.act, widened = "health", " (LLM intent fallback: health request)"
                d = dialogue.decide(a, self.p.settings.max_follow_ups, self.p.settings.adaptive_slot_questions)
        enc, es = getattr(self.p, "encoder", None), s.get("emergency_score")
        if (enc is not None and es is not None and es >= enc.tau_ask and d.kind in ("ask", "proceed") and a.act in ("health", "answer")
                and "danger" not in a.asked_slots and a.danger_answer is None and a.questions_asked < self.p.settings.max_follow_ups + 1
                and not self.p.safety.denied_flags(s["facts"].safety_text_norm or s["facts"].text_norm)):
            d = dialogue.danger_decision(a.language)   # grey-zone score: one danger-sign question before anything else
        current_mood = mood.detect(" ".join(a.scoped_user))
        area = delhi.resolve(" ".join(a.scoped_user), s["request"].location)
        step = pathways.conversation_step(a, s["request"].patient_context, current_mood)
        if step:
            d = (dialogue.DialogueDecision("ask", step.question, [o["label"] for o in step.options],
                                          f"pathway:{step.pathway}:{step.question_id}", "deterministic pathway")
                 if step.kind == "question" else dialogue.DialogueDecision("proceed", reason="pathway disposition"))
        if current_mood.danger_first and a.act in ("health", "answer") and "danger" not in a.asked_slots and not any(
                slot.startswith("pathway:") for slot in a.asked_slots) and not step:
            d = dialogue.danger_decision(a.language)
        if current_mood.unsure_is_yes and "danger" in a.asked_slots and a.danger_answer is None:
            # An uncertain or unrecognised danger reply cannot clear a panic screen.
            step = pathways.Step("disposition", "panic", disposition="emergency", care_type="emergency_112",
                                 urgency="emergency", why="Danger signs could not be ruled out during panic.")
            d = dialogue.DialogueDecision("proceed", reason="uncertain danger answer")
        if current_mood.max_questions and a.questions_asked >= current_mood.max_questions and d.kind == "ask":
            d = dialogue.DialogueDecision("proceed", reason="mood question cap; offer human call-back")
        return {"dialogue": d, "pathway": step, "mood": current_mood, "service_area": area, **_t("converse", f"intent={a.act}{' +correction' if a.correction else ''}; new_topic={a.new_topic}; "
                                                f"questions asked={a.questions_asked}; decision={d.kind}{widened}; mood={current_mood.label}; "
                                                f"service_area={area['name'] if area else None}"
                                                f"{' (' + d.reason + ')' if d.reason else ''}")}

    @staticmethod
    def after_converse(s: TriageState) -> list[str] | str:
        if s["dialogue"].kind in ("reply", "ask"):
            return "reply_guard"
        return ["classify", "llm_safety", "llm_triage"]  # parallel fan-out

    def reply_guard(self, s: TriageState) -> dict:
        """Chit-chat / refusal / slot-question turns still get the LLM safety screen, so wording the
        rules and the dialogue lexicon do not know can never skip safety. Rules remain the floor."""
        out = self.llm_safety(s)
        sr = out.get("llm_safety")
        present = [x.flag for x in (sr.findings if sr else []) if x.status == "present" and x.flag in RED_FLAGS]
        possible = [x.flag for x in (sr.findings if sr else []) if x.status == "possible" and x.flag in RED_FLAGS]
        det = self.p.router.predict(s["facts"])
        if present or det.care_type == "emergency_112":
            out["decision"] = {"outcome": "emergency", "flags": present, "basis": "model_guard", "escalated_by": ["llm_reply_guard"] if present else [det.source]}
        elif (possible and sr and sr.screening_question
              and s["facts"].analysis.questions_asked < min(4, s["mood"].max_questions or 4)
              and not any(t["role"] == "assistant" and t["content"].strip() == sr.screening_question.strip()
                          for t in s["facts"].history)):
            out["decision"] = {"outcome": "follow_up", "question": sr.screening_question, "options": sr.screening_options or None,
                               "basis": "safety_screen", "possible": possible}
        elif possible:
            out["decision"] = {"outcome": "emergency", "flags": possible, "basis": "safety_screen", "escalated_by": ["possible_flag_no_budget"]}
        return out

    @staticmethod
    def after_guard(s: TriageState) -> str:
        d = s.get("decision")
        return {"emergency": "emergency", "follow_up": "follow_up"}.get(d["outcome"], "dialogue_reply") if d else "dialogue_reply"

    def dialogue_reply(self, s: TriageState) -> dict:
        d = s["dialogue"]
        resp = TriageResponse(follow_up_question=d.message, reasoning=("UNREVIEWED (demo pathway)." if s.get("pathway") else "") + self._mood_text(s), answer_options=d.options)
        if s.get("pathway") and s.get("service_area"):
            notes = delhi.seasonal_notes(s["pathway"], self.p.matcher.now().month)
            if notes:
                resp.reasoning += " Seasonal context (UNREVIEWED): " + " ".join(notes)
        return {"response": resp, **_t("dialogue_reply", f"{d.kind}: {d.slot or s['facts'].analysis.act}")}

    # -- 3a. deterministic classifier slot ---------------------------------
    def classify(self, s: TriageState) -> dict:
        d = self.p.router.predict(s["facts"])
        return {"det": d, **_t("classify", f"{self.p.router.name}: {d.care_type} (conf {d.confidence:.2f}) evidence={d.evidence}")}

    # -- 3b/3c. LLM nodes ----------------------------------------------------
    def _case(self, s: TriageState) -> str:
        f = s["facts"]
        return render_case(language=f.language, history=f.history, message=f.latest_input,
                           follow_ups_asked=f.n_follow_ups_asked)

    def _llm(self, role: str):
        llm = self.p.llm
        return llm.for_role(role) if hasattr(llm, "for_role") else llm

    def llm_safety(self, s: TriageState) -> dict:
        if not self.p.llm or not self._llm("safety").enabled:
            return {"llm_safety": None, **_t("llm_safety", "skipped (LLM off)")}
        pr = load(SAFETY_PROMPT)
        try:
            out = self._llm("safety").structured(pr.text, self._case(s), SafetyReview, max_tokens=600)
            return {"llm_safety": out, **_t("llm_safety", f"{pr.tag}: " + (", ".join(f"{x.flag}:{x.status}" for x in out.findings) or "no findings"))}
        except LLMError as e:
            log.warning("llm_safety failed: %s", e)
            return {"llm_safety": None, **_t("llm_safety", f"{pr.tag} failed ({e}); rules remain the safety floor")}

    def llm_triage(self, s: TriageState) -> dict:
        if s.get("pathway") or not self.p.llm or not self._llm("triage").enabled:
            return {"llm_triage": None, **_t("llm_triage", "skipped (LLM off)")}
        pr = load(TRIAGE_PROMPT)
        try:
            out = self._llm("triage").structured(pr.text, self._case(s), TriageAssessment)
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
        cap = min(st.max_follow_ups, s["mood"].max_questions or st.max_follow_ups)
        budget_left = f.n_follow_ups_asked < cap

        present = [x.flag for x in (sr.findings if sr else []) if x.status == "present"]
        possible = [x.flag for x in (sr.findings if sr else []) if x.status == "possible"]
        flags = list(dict.fromkeys([*present, *(tr.red_flags if tr else [])]))
        flags = [x for x in flags if x in RED_FLAGS]

        # Guard: any source may escalate.
        escalators = []
        if flags:
            escalators.append("llm")
        if tr and (tr.care_type == "emergency_112" or tr.urgency == "emergency"):
            escalators.append("llm_triage")
        if det.care_type == "emergency_112":
            escalators.append(det.source)
        if escalators:
            d = {"outcome": "emergency", "flags": flags, "basis": "model_guard", "escalated_by": escalators}
            return {"decision": d, **_t("fuse", f"escalated to 112 by {escalators}; flags={flags}")}

        if possible:
            q = sr.screening_question if sr else None
            already_asked = bool(q) and any(t["role"] == "assistant" and
                " ".join(t["content"].casefold().split()) == " ".join(q.casefold().split()) for t in f.history)
            if f.analysis.questions_asked < min(4 if s.get("pathway") else st.max_follow_ups, s["mood"].max_questions or 4) and q and not already_asked:
                d = {"outcome": "follow_up", "question": q, "options": sr.screening_options or None, "basis": "safety_screen", "possible": possible}
                return {"decision": d, **_t("fuse", f"possible red flag {possible}: asking one danger-sign question")}
            d = {"outcome": "emergency", "flags": possible, "basis": "model_guard", "escalated_by": ["possible_flag_no_budget"]}
            return {"decision": d, **_t("fuse", f"possible red flag {possible} and no question budget left -> 112 as a precaution")}

        step = s.get("pathway")
        if step and step.kind == "disposition":
            if step.disposition == "emergency":
                d = {"outcome": "emergency", "flags": [], "basis": "pathway", "escalated_by": [step.rule or step.pathway]}
            else:
                d = {"outcome": "route", "care_type": step.care_type, "urgency": step.urgency, "basis": "pathway"}
            return {"decision": d, **_t("fuse", f"pathway={step.pathway}; rule={step.rule}; raised_by={step.raised_by}")}

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
                ct, basis = (llm_ct, "llm") if llm_ct else (None, None)
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
                previous = {" ".join(t["content"].casefold().split()) for t in f.history if t["role"] == "assistant"}
                if " ".join(q.casefold().split()) in previous:
                    q, opts = follow_up.next_question(f)
                    src = "template"
                d = {"outcome": "follow_up", "question": q, "options": opts, "basis": f"ask_{src}"}
                return {"decision": d, **_t("fuse", f"not enough detail -> one follow-up question ({src}); policy={policy}")}
            ct, basis = st.fallback_care_type, "fallback"

        enc = getattr(self.p, "encoder", None)
        if (ct and budget_left and enc is not None and enc.tau_margin > 0 and det.source == "encoder" and det.margin is not None
                and det.runner_up and det.margin < enc.tau_margin and (tr is None or llm_ct != det_ct or llm_ct is None)):
            aq = follow_up.ambiguity_question(f, det_ct, det.runner_up) if det_ct == ct else None
            if aq and "ambiguity" not in (f.analysis.asked_slots if f.analysis is not None else []):
                d = {"outcome": "follow_up", "question": aq[0], "options": aq[1], "basis": "ask_ambiguity"}
                return {"decision": d, **_t("fuse", f"encoder cannot separate {det_ct} from {det.runner_up} (log-ratio {det.margin:.3f} < {enc.tau_margin}) -> one two-option question")}

        a = f.analysis
        if (st.timing_question and ct in ("paramedic_home_visit", "home_nursing") and a is not None and a.asked_slots
                and "timing" not in a.asked_slots and dialogue.timing_of(a) is None and "timing" not in a.known_slots
                and "unknown" not in a.known_slots.values()   # the user is not engaging ("pata nahi"): do not push another question
                and f.n_follow_ups_asked <= st.max_follow_ups
                and (not s["mood"].max_questions or f.n_follow_ups_asked < cap)):
            q = dialogue.timing_question(a)
            d = {"outcome": "follow_up", "question": q.message, "options": q.options, "basis": "ask_timing"}
            return {"decision": d, **_t("fuse", f"{ct} is a visit and timing is unknown -> one question about when it is needed")}

        urgency = tr.urgency if basis == "llm" and tr and tr.urgency else urgency_for(ct)
        d = {"outcome": "route", "care_type": ct, "urgency": urgency, "basis": basis, "policy": policy, "agreement": agreement,
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
                              reasoning=explain.emergency_text(safety, f.language) + (" UNREVIEWED (demo). " + (s["pathway"].why or "") if s.get("pathway") else ""), matched_caregivers=[])
        return {"response": resp, **_t("emergency", f"112 response; flags={safety.flags}; source={safety.source}")}

    def follow_up(self, s: TriageState) -> dict:
        d = s["decision"]
        resp = TriageResponse(follow_up_question=d["question"], reasoning="", answer_options=d.get("options"))
        return {"response": resp, **_t("follow_up", d["basis"])}

    def match(self, s: TriageState) -> dict:
        f, d, req = s["facts"], s["decision"], s["request"]
        tr: TriageAssessment | None = s.get("llm_triage")
        ct = d["care_type"]
        urgency = d["urgency"]
        timing, timing_src = dialogue.effective_timing(f.analysis)  # stated, else inferred from severity words, else today
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
        if d["basis"] == "llm":
            required += [{skill} for skill in sorted(llm_skills)]
        cands = self.p.matcher.match(ct, urgency, required, hints | llm_skills, f.language, (req.location or delhi.matching_location(s.get("service_area"))), timing)
        return {"candidates": cands, **_t("match", f"{len(cands)} eligible; required={[sorted(g) for g in required]} "
                                                    f"skills={sorted(hints | llm_skills)}; availability={timing} ({timing_src})",
                                         ranking=[{"id": c.caregiver_id, "score": c.score, **c.components} for c in cands])}

    @staticmethod
    def _mood_text(s):
        m = s.get("mood")
        if not m:
            return ""
        if m.human_callback:
            return " I'm sorry this has been frustrating. You can request a human call-back from the care team."
        if m.label == "anxiety":
            return " We will take this one step at a time and check the warning signs first."
        if m.label == "panic":
            return " Take this one step at a time. If there is immediate danger, call 112."
        return ""

    def respond(self, s: TriageState) -> dict:
        f, d = s["facts"], s["decision"]
        tr: TriageAssessment | None = s.get("llm_triage")
        ct, cands = d["care_type"], s["candidates"]
        if d["basis"] == "pathway":
            step = s["pathway"]
            reasoning = "UNREVIEWED (demo). " + (step.why or "")
            if step.raised_by:
                reasoning += f" Caution increased for {step.raised_by}."
            # Advice is supplied only by the existing sourced pathway content.
            if step.advice:
                reasoning += " " + step.advice
            if not cands:
                reasoning += explain.no_match_suffix(f.language)
        elif d["basis"] == "llm" and tr and tr.reasoning:
            reasoning = tr.reasoning
            if not cands:
                reasoning += explain.no_match_suffix(f.language)
        else:
            stub = RouteDecision(ct, d["model"]["confidence"], s["det"].evidence, d["basis"])
            reasoning = explain.decision_text(f, stub, ct, fallback=d["basis"] == "fallback", no_match=not cands)
        resp = TriageResponse(
            care_type=ct, urgency=d["urgency"], red_flags=[], reasoning=reasoning + self._mood_text(s),
            matched_caregivers=[MatchedCaregiver(caregiver_id=c.caregiver_id, score=c.score, reason=c.reason) for c in cands],
        )
        return {"response": resp, **_t("respond", f"reasoning from {'llm' if d['basis'] == 'llm' else 'template'}")}
