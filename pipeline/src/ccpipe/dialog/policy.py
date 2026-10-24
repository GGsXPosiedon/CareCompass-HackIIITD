"""Follow-up policy: decide the next action from the whole conversation.

Actions: crisis_safety | defer_to_safety | acknowledge_decline | deescalate | redirect | greet | offer_exit | ask | commit
Rules:
  * Safety first: crisis text and emergency signs are handed to the safety path, never answered with a question.
  * Redirects (greeting, off-topic, gibberish) and emotional replies do NOT count toward the question budget.
  * Only recognised slot questions count (max_questions, default 2); a slot is never asked twice or when already answered.
  * A refusal is respected: no booking, no further questions. Emotion never lowers urgency and never forces a care type.
  * This policy never chooses a care type. `commit` means "enough information; hand over to the router"."""
from __future__ import annotations

from dataclasses import dataclass, field

from .slots import filled_from_text, render, slot_of_assistant
from .turns import TurnInfo, cfg, classify, detect_language


@dataclass
class Decision:
    action: str
    message: str | None = None
    slot: str | None = None
    options: list[str] | None = None
    counts_toward_budget: bool = False
    reason: str = ""
    known: dict = field(default_factory=dict)
    symptoms: list[str] = field(default_factory=list)


def _reply(key: str, lang: str) -> str:
    return cfg()["replies"][key][lang]


def decide(history: list[dict], user_input: str, max_questions: int | None = None) -> Decision:
    """history: [{'role': 'user'|'assistant', 'content': str}, ...] before `user_input`."""
    c = cfg()
    max_q = max_questions if max_questions is not None else c["max_questions"]
    lang = detect_language(user_input)
    asked: list[str] = []
    known: dict = {}
    symptoms: list[str] = []
    pending = None
    infos: list[TurnInfo] = []
    turns = list(history) + [{"role": "user", "content": user_input}]
    for m in turns:
        if m["role"] == "assistant":
            pending = slot_of_assistant(m["content"])
            if pending:
                asked.append(pending)
            continue
        info = classify(m["content"], awaiting_answer=pending is not None)
        infos.append(info)
        known.update(filled_from_text(m["content"], pending))
        for s in info.symptoms:
            if s not in symptoms:
                symptoms.append(s)
        pending = None
    cur = infos[-1]
    base = dict(known=known, symptoms=symptoms)
    if cur.language != "en" or lang != "en":
        lang = cur.language
    elif len(infos) > 1:  # keep the conversation's language when the current message is too short to tell
        lang = next((i.language for i in reversed(infos[:-1]) if i.language != "en"), "en")

    if "crisis" in cur.flags:
        return Decision("crisis_safety", _reply("crisis", lang), reason="self-harm wording; hand to safety path", **base)
    if "emergency_sign" in cur.flags:
        return Decision("defer_to_safety", None, reason="emergency symptom named; safety rules decide", **base)
    if "decline" in cur.flags:
        return Decision("acknowledge_decline", _reply("decline", lang), reason="user refused care; do not book or keep asking", **base)
    if "abuse" in cur.flags:
        return Decision("deescalate", _reply("deescalate", lang), reason="frustration; stop pushing", **base)
    no_content_run = 0
    for i in reversed(infos):
        if i.primary in ("no_health", "greeting"):
            no_content_run += 1
        else:
            break
    if cur.primary == "greeting":
        return Decision("greet", _reply("greeting", lang), reason="greeting only", **base)
    if cur.primary == "no_health" and not symptoms:
        key = "offer_exit" if no_content_run >= 4 else "no_health"
        return Decision("offer_exit" if key == "offer_exit" else "redirect", _reply(key, lang), reason="no health content; not counted", **base)
    if cur.primary == "distress" and not symptoms:
        return Decision("redirect", _reply("distress", lang), reason="distress without symptoms; invite detail", **base)
    if not symptoms:  # an answer turn but no symptom ever stated
        return Decision("redirect", _reply("no_health", lang), reason="no symptom stated yet", **base)

    main = symptoms[0]
    order = c["slot_order"]["fever" if main == "fever" else "pain" if main in c["pain_symptoms"] else "default"]
    if len(asked) < max_q:
        for slot in order:
            if slot in asked or slot in known:
                continue
            if slot.startswith("severity") and "severity" in known:
                continue
            text, opts = render(slot, main, lang)
            return Decision("ask", text, slot, opts, True, f"missing slot: {slot}", **base)
    return Decision("commit", None, reason="questions exhausted or slots filled", **base)
