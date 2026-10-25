# CareCompass backend

FastAPI + **LangGraph** service that turns a family's message (English / Hindi / Hinglish) into the
organiser contract: `care_type`, `urgency`, `red_flags`, an optional single `follow_up_question`, plain-language
`reasoning` and up to 3 `matched_caregivers`.

```bash
# one-time: install uv (https://docs.astral.sh/uv/) -> Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
uv sync                              # creates .venv with the locked deps (Python 3.12 via .python-version)
cp .env.example .env                 # add GEMINI_API_KEY (optional: without it the deterministic path runs)
uv run uvicorn app.main:app --reload # http://127.0.0.1:8000/docs
uv run pytest -q                     # mocked provider tests; encoder tests need optional NumPy
uv run python -m eval.run_eval       # judging metrics -> eval/report.md (exit 1 if any emergency is missed)
```

Dependencies live in `pyproject.toml` and are pinned in `uv.lock` (commit both). Add a package with
`uv add <pkg>`, a dev-only one with `uv add --dev <pkg>`.

The deployment review passed 267 checks with 1 skipped after excluding `tests/test_encoder_router.py`, which imports NumPy not installed by the base dependency set. Install the encoder extras (`uv sync --extra encoder`) for full encoder test collection. Hosting instructions and the in-memory booking limitation are in [the deployment guide](../docs/DEPLOYMENT.md).

## Endpoints

| Method & path | Purpose |
|---|---|
| `POST /triage` (also `/api/v1/triage`, `/api/v1/route`) | Organiser contract. Uses conversation text only; legacy `patient_context` fields are ignored. |
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
| `llm_triage` | Gemini with the *triage analyst* prompt: service, skills, one follow-up question if needed, reasoning, based only on the conversation. |
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
- `llm_first` (default now): Gemini chooses the service or a contextual follow-up. The placeholder rule classifier does not override a successful Gemini question. Rules remain the fallback when Gemini is unavailable; emergency rules always run first.
- `model_first`: use when your trained model is in place; LLM is the fallback.
- `agree_or_ask`: if both decide and disagree, ask one clarifying question.
Agreement between the two is logged in the trace for analysis.

## System prompts (`app/prompts/`)
Versioned Markdown files with a front-matter header (`id`, `version`, `node`, `output_schema`):
- `safety_screener.md`: red-flag definitions with Hindi/Hinglish cues, present-vs-possible rules, negation and history handling, screening question, examples.
- `triage_analyst.md`: service definitions and tie-breaks, follow-up policy, skills vocabulary, avoid assuming who the patient is, language/tone rules, examples.

Both prompts treat `<history>`, `<user_message>` and `PROFILE` as untrusted data (prompt-injection guard). Prompt tags (`triage_analyst@1.2.0`) appear in the trace.

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

Ties go to whoever is free sooner. Every Gemini-required skill is enforced independently; no matches are returned when nobody qualifies. The `reason` string is built only from real profile fields (top two factors + availability window).

## Evaluation (`eval/`)
`run_eval.py` scores any JSONL in our gold format or the organiser's nested format against the judging questions: emergency recall (must be 100%), false-alarm rate, care-type/urgency accuracy per language, asking on vague input vs needless questions, caregiver validity vs the organiser baseline, and explainability. See `eval/report.md` for the latest run.
`gold_cases.jsonl` is a small hand-written set (52 cases). The rules were tuned against it, so it overstates real accuracy; use it as a regression gate, not as a benchmark.

## Configuration
See `.env.example`. Key settings: `GEMINI_API_KEY`, `GEMINI_MODEL`, `LLM_BACKEND`, `ROUTER_BACKEND`, `FUSION_POLICY`, `MODEL_TRUST_THRESHOLD`, `MAX_FOLLOW_UPS`, `CAREGIVERS_PATH`.
Saved patient profiles are not accepted or sent to providers. The assistant uses only conversation text and asks when the identity of the person needing care matters.

## Conversational development setup

The default model is `gemini-3.5-flash`, verified with a neutral live greeting. Set `GEMINI_MODEL` in `backend/.env` to change it. Gemini 3 uses `GEMINI_THINKING_LEVEL=low`; legacy Gemini 2.5 models use `GEMINI_THINKING_BUDGET`. Temporary HTTP 502/503/504 responses get one retry. HTTP status codes are logged without keys or provider response bodies.

Responses include `response_source` (`gemini`, `rules`, or `safety_rules`) and an optional `service_notice` when any Gemini check falls back. The UI displays that notice so fallback answers cannot silently look like live Gemini replies. `/health` reports configuration; a configured model name alone does not prove a successful provider call.

Text and voice share the same history. Assistant turns may carry `kind` (`follow_up`, `recommendation`, `emergency`); a completed recommendation resets the next clarification budget. Legacy turns without `kind` remain supported. The frontend sends at most 40 history turns and keeps the complete saved transcript locally. Repeated ordinary questions are replaced; an unresolved possible danger sign that would repeat its screening question escalates rather than looping.

## Supplied caregiver roster

The default repository is `app/data/caregivers.csv`, copied from the supplied `HackIIITD/caregivers.csv`: 60 unique caregivers (18 doctors, 28 medics, 14 phlebotomists), with 52 active. Matching retains active, role, skill, distance and availability filters; the roster does not create real appointments. Set `CAREGIVERS_PATH` to override the file. The source CSV outside this repository was left unchanged.

The synthetic `caregivers_seed.csv` remains a regression-test fixture. Tests explicitly select that fixture, while roster integration checks load the supplied data and verify that the default API returns `CG_` profiles.

## Audit corrections

`TriageAssessment.urgency` allows Gemini to distinguish routine scheduled care from same-day needs. Emergency urgency alone triggers the guard. Each Gemini-required skill is a hard filter; unavailable skill combinations return no matches rather than relaxing requirements. Matching also excludes caregivers whose slots for the recommendation date are all booked. Invalid dates and incomplete/out-of-range coordinates on caregiver lookup return 422.

Responses include `response_language` so Hindi voice replies can preserve their script and playback language. `eval.run_eval --llm off` reports macro-F1 and actual response sources in addition to accuracy. The full requirements and submission-gap review is in `../docs/PROJECT_AUDIT.md`.
