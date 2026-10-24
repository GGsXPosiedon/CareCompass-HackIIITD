# CareCompass backend

FastAPI + **LangGraph** service that turns a family's message (English / Hindi / Hinglish) into the
organiser contract: `care_type`, `urgency`, `red_flags`, an optional single `follow_up_question`, plain-language
`reasoning` and up to 3 `matched_caregivers`.

```bash
# one-time: install uv (https://docs.astral.sh/uv/) -> Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync                              # creates .venv with the locked deps (Python 3.12 via .python-version)
cp .env.example .env                 # add GEMINI_API_KEY (optional: without it the deterministic path runs)
uv run uvicorn app.main:app --reload # http://127.0.0.1:8000/docs
uv run pytest -q                     # 89 tests, no network
uv run python -m eval.run_eval       # judging metrics -> eval/report.md (exit 1 if any emergency is missed)
```

Dependencies live in `pyproject.toml` and are pinned in `uv.lock` (commit both). Add a package with
`uv add <pkg>`, a dev-only one with `uv add --dev <pkg>`.

## Endpoints

| Method & path | Purpose |
|---|---|
| `POST /triage` (also `/api/v1/triage`, `/api/v1/route`) | Organiser contract. Accepts optional `patient_context` (saved family profile). |
| `POST /api/v1/triage/trace` | Same decision + a plain-language trace of every graph node and the caregiver score breakdown ("why did it decide this?"). |
| `GET /api/v1/graph` | Mermaid source of the triage graph. |
| `GET /caregivers?ids=&care_type=&lat=&lng=&date=` | Profiles + free slots for the matched ids. |
| `POST /bookings` | Book a slot (409 on clash / past / unavailable). |
| `GET /health` | Classifier, LLM model, ruleset version, fusion policy. |

## The triage graph (`app/graph/`)

```
START → intake → rules_safety ──fired──▶ emergency (112, no caregivers) → END
                      │ clear
          ┌───────────┼─────────────┐            (run in parallel)
       classify   llm_safety    llm_triage
   (model slot)  (Gemini, recall) (Gemini, service)
          └───────────┼─────────────┘
                     fuse ──escalate──▶ emergency
                      │  ──ask────────▶ follow_up (one question + options) → END
                      ▼ route
                    match → respond → END
```

| Node | What it does |
|---|---|
| `intake` | Normalises text, detects language, extracts tri-state facts (present / denied / unknown), counts questions already asked. |
| `rules_safety` | Versioned regex red-flag engine (`app/rules/redflags.json`, EN/HI/Hinglish, negation-aware). If it fires, **no model is consulted**. |
| `classify` | **Your model slot.** Today: transparent rules (`RuleRouter`). Later: your trained classifier, same `predict(facts) -> RouteDecision` interface, `ROUTER_BACKEND=<name>`. |
| `llm_safety` | Gemini with the *safety screener* prompt: only red flags, `present` vs `possible`, recall over precision. |
| `llm_triage` | Gemini with the *triage analyst* prompt: service, skills, one follow-up question if needed, reasoning, uses the saved profile. |
| `fuse` | Safety guard + combination policy (below). |
| `match` / `respond` | Caregiver ranking, then the contract response (validated before it leaves). |

### Safety contract (tested)
1. Rules run first; a rules emergency cannot be overridden by anything.
2. Any source (LLM screener, LLM triage, your classifier) can **escalate** to `emergency_112`; none can de-escalate.
3. A `possible` red flag is never dropped: the graph asks one danger-sign question (e.g. "Is the baby under 3 months?");
   if the question budget (2) is used up, it escalates as a precaution.
4. Emergency ⇒ `matched_caregivers = []`; follow-up ⇒ no decision fields. Enforced by the `TriageResponse` validator.
5. If Gemini fails, times out, or returns anything that violates the schema, the deterministic path answers.

### Fusion policy (`FUSION_POLICY`)
- `llm_first` (default now): LLM decides; if it wants to ask but your classifier is confident (≥ `MODEL_TRUST_THRESHOLD`, 0.85) the classifier answers instead, so no needless question.
- `model_first`: use when your trained model is in place; LLM is the fallback.
- `agree_or_ask`: if both decide and disagree, ask one clarifying question.
Agreement between the two is logged in the trace for analysis.

## System prompts (`app/prompts/`)
Versioned Markdown files with a front-matter header (`id`, `version`, `node`, `output_schema`):
- `safety_screener.md`: red-flag definitions with Hindi/Hinglish cues, present-vs-possible rules, negation and history handling, screening question, examples.
- `triage_analyst.md`: service definitions and tie-breaks, follow-up policy, skills vocabulary, how to use the family profile, language/tone rules, examples.

Both prompts treat `<history>`, `<user_message>` and `PROFILE` as untrusted data (prompt-injection guard). Prompt tags (`triage_analyst@1.0.0`) appear in the trace.

## Schema enforcement
- **Requests:** `TriageRequest` types/ranges are validated (422 on bad input); unknown keys ignored for harness compatibility.
- **LLM outputs:** `app/schemas/llm.py` (`SafetyReview`, `TriageAssessment`) are `extra="forbid"` with closed `Literal` enums for care type, red flags and skills. The *same* models generate Gemini's `responseSchema`
  (constrained decoding), and the reply is re-validated with Pydantic. Over-long strings/lists are clipped; wrong types or unknown labels fail the call → fallback.
- **Responses:** `TriageResponse` is `extra="forbid"` with invariants (red flags ⇒ emergency; emergency ⇒ no caregivers; follow-up ⇒ no decision).

## Caregiver scoring (`app/services/matching.py`)
**Hard constraints first** (a caregiver failing any is never shown): active · right role for the care type (Medic for home visit/nursing, phlebotomist for lab, doctor for teleconsult) · has every *required* skill (e.g. injection → `injection_im|injection_iv`) · within their own service radius · free in the needed window (same-day: still has a slot today).

**Then a soft score in [0,1]**, the same blend as the organiser's reference labels so scores are comparable:

| Component | Weight | How it is computed |
|---|---|---|
| Language | 0.35 | 1 if the caregiver speaks the family's language (Hindi for Hindi/Hinglish, English for English), else 0 |
| Proximity | 0.30 | `1 − distance_km / caregiver_radius_km` (dropped and weights renormalised for teleconsultation or no location) |
| Skill | 0.20 | `0.85 × coverage of needed/preferred skills + 0.15 × tier` (tier only for Medics) |
| Rating | 0.15 | `rating / 5` |

Ties go to whoever is free sooner. Gemini-suggested skills are applied as a requirement first and relaxed if nobody qualifies. The `reason` string is built only from real profile fields (top two factors + availability window).

## Evaluation (`eval/`)
`run_eval.py` scores any JSONL in our gold format or the organiser's nested format against the judging questions: emergency recall (must be 100%), false-alarm rate, care-type/urgency accuracy per language, asking on vague input vs needless questions, caregiver validity vs the organiser baseline, and explainability. See `eval/report.md` for the latest run.
`gold_cases.jsonl` is a small hand-written set (52 cases). The rules were tuned against it, so it overstates real accuracy; use it as a regression gate, not as a benchmark.

## Configuration
See `.env.example`. Key settings: `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_BACKEND`, `ROUTER_BACKEND`, `FUSION_POLICY`, `MODEL_TRUST_THRESHOLD`, `MAX_FOLLOW_UPS`, `CAREGIVERS_PATH`.
Health data from the Profile is sent to Gemini only when the user leaves "Share with the care assistant" on.
