# CareCompass audit against the final problem statement

Audit date: 25 October 2026. This is a prototype-readiness review, not a clinical validation or a hidden-test score.

## Reference and scope

- Organiser reference: [CareCompass_CAI_Problem_Statement_Final.pdf](C:/Users/dipes/Coding/Hackathons/HackIIITD/CareCompass_CAI_Problem_Statement_Final.pdf), all 5 pages; the indicative API and scoring table on page 4 were also inspected visually.
- Repository reference: `problem_statement.md`.
- Inspected the React shell, routes, history, profile sharing, voice adapters, FastAPI endpoints, request/response schemas, LangGraph fusion, prompts, deterministic safety, caregiver filters/ranking, CSV repository, booking reservation, tests and evaluation tooling.
- Used the supplied 60-caregiver roster. Training on the other machine was outside this checkout and was not treated as implemented here. No Git commands were run.

## Outcome

The API-first intake -> triage -> matching -> demo booking flow is implemented and tested. The main remaining submission risks are the absent hidden-test predictions, unverified final organiser taxonomy/schema, trained-model integration, independent clinical review and the final write-up/video. The repository should be presented as a working Gemini-assisted prototype, not a clinically validated or fully submitted solution.

## Issues fixed during this audit

| Finding | Change and evidence |
|---|---|
| Deep-linked Profile had no obvious way back | Added a persistent top-bar Back control on supporting pages. Normal navigation uses in-app history; direct Profile loads fall back to Settings and Services to Bookings. Direct-load fallback replaces history so Back cannot bounce between the same two pages. |
| Hindi speech could be recognised/responded to as English | New sessions use Auto rather than forcing English. Sarvam remains in `transcribe` mode with automatic language detection; it never requests translation ([provider mode reference](https://docs.sarvam.ai/api/api-guides-tutorials/speech-to-text/how-to/select-output-mode)). Browser Auto uses Hindi recognition as an India-focused fallback, while explicit English remains available. Hindi/Hinglish playback is selected from the text. Backend responses expose their resolved language, including emergency responses. |
| Required Gemini skills could be relaxed when nobody matched | Each declared required skill is now an independent hard condition for a Gemini routing decision. No candidate is returned when nobody has all required skills; the system does not silently lower the requirement. |
| A completely booked caregiver could remain in the ranking | Eligibility now checks remaining, unbooked slots for the same date the UI opens: today for same-day care and tomorrow for scheduled care. |
| Gemini urgency was discarded in favour of a care-type lookup | Added a validated urgency field to the Gemini assessment. A routine consultation can be scheduled; explicit emergency urgency escalates even when the model's care-type field conflicts. Rules-only routing retains its conservative defaults. |
| Invalid caregiver date/location filters could produce server errors or be silently ignored | Invalid dates, out-of-range coordinates and incomplete coordinate pairs now return HTTP 422. |
| Audit metrics did not include the stated judging metric | Added care-type and urgency macro-F1 to the offline evaluation, plus actual response-source counts so fallback answers cannot be mistaken for successful Gemini output. |

The landing screen also has quiet contour patterns. The existing compact composer, persistent icon rail, bottom Settings, five Recents and full History were retained.

## Requirements coverage

| Final problem-statement requirement | Status | Evidence or remaining limit |
|---|---|---|
| English, Hindi and Hinglish text/voice input | Implemented; real microphone QA remains | Language-aware API, transcription and playback adapters; automated Hindi preservation checks. Browsers do not offer reliable speech-language auto-detection, so explicit Hindi/English selection remains available. |
| Targeted follow-up questions | Partial alignment | Gemini uses conversation/profile context, avoids repeated questions and respects the configured budget. Default is up to 2 questions; the brief says 2-4, while tie-breaks prefer fewer. Confirm whether the organiser mandates a fixed minimum. Clear requests currently route immediately. |
| Care type and urgency | Implemented, taxonomy confirmation pending | Closed enums and explicit urgency. Current types are paramedic_home_visit, home_nursing, lab_test_home, teleconsultation and emergency_112. The brief also mentions specialists; no specialist label is added without the final taxonomy and matching data. |
| Immediate emergency path, no caregiver matching | Implemented and regression-tested | Deterministic rules precede models. Any emergency source escalates, and final response validation prohibits emergency caregiver matches. |
| Matching by skills, distance, availability, language and rating | Implemented; expert ranking quality unmeasured | Active/role/required-skill/radius/available-slot filters, weighted explainable ranking and real roster profiles. Language is a preference rather than a hard exclusion; there is no expert-judged ranking dataset in this checkout. |
| Plain-language explanations | Implemented | Gemini reasoning or visible fallback reasoning; each returned caregiver includes a reason derived from profile fields. |
| End-to-end demo booking | Implemented prototype | Fresh availability, conflict recovery, atomic in-memory slot reservation and confirmation. Bookings reset on server restart and do not dispatch real caregivers. |
| API-first published schema | Indicative shape implemented | Pydantic request/response models and aliases are covered by tests. The final organiser schema is not present separately; optional UI metadata must be checked against its allowance for extra fields. |
| Synthetic-only inputs and declared public datasets | Prototype support, operational discipline required | Supplied mock roster and handwritten synthetic regression cases. No external training dataset was uploaded or evaluated in this audit. Profile consent and local-chat deletion controls exist; a real-patient production data system is not implemented. |
| Affordable model APIs allowed and declared | Implemented | Gemini chat/safety, Sarvam voice when configured, browser speech fallback. No extra OpenAI-compatible keys were added. The trained classifier remains a future integration. |

## Deliverable checklist

| Required deliverable | State |
|---|---|
| REST API | Present; reconcile with the final organiser schema before submission. |
| Demo interface | Present; browser and automated checks cover major flows. Live Hindi microphone accuracy and speaker quality still require a device test. |
| Hidden-test predictions CSV | Missing. No hidden-test input or verified output schema exists in this checkout. Do not label the local 52-case evaluation as hidden-test predictions. |
| Repository, README and setup | Present locally with the Windows launcher. Remote/push state was not inspected because Git commands are prohibited. Docker is preferred by the brief and is not supplied. |
| Short write-up, maximum 2 pages | No final standalone submission write-up found. Existing architecture/README documentation is longer and should not be passed off as this deliverable. |
| Demo video, maximum 3 minutes | No final CareCompass submission video found in the repository. The supplied Claude reference recording is not the required demo. |

## Reproducible validation

Commands: `cd frontend; npm.cmd run build; npm.cmd test` and `cd backend; .venv/Scripts/python.exe -m pytest -q; .venv/Scripts/python.exe -m eval.run_eval --llm off`.

**Validation result:** production frontend build passes; **64 frontend tests and 105 backend tests pass**. Browser checks verified direct `/profile` -> Back -> `/settings` -> Back -> `/care`, with no loop, and Auto selected on a fresh load.

The offline evaluation uses 52 handwritten cases, a fixed 24 October 2026 12:00 IST clock and the supplied roster. Its actual sources are 22 deterministic safety responses and 30 rules responses; Gemini is disabled.

| Metric | Observed |
|---|---|
| Emergency recall | 21/21 (100%) |
| False-alarm rate | 1/31 non-emergency cases (3.2%) |
| Care-type accuracy | 47/48 labelled routing cases (97.9%) |
| Care-type macro-F1 | 0.9800 |
| Urgency macro-F1 | 0.9666 |
| Returned caregiver role, required skills, availability and radius checks | 100% on this case set |
| Preferred-language match rate | 77.9%; a ranking preference, not a guarantee |

These numbers are regression evidence on a small in-house set. They are not estimates of clinical reliability, expert ranking quality, live Gemini accuracy or hidden-test performance. See `backend/eval/report.md` for the generated results.

## Known limitations and recommended submission order

1. Reconcile the final taxonomy, urgency definitions, follow-up budget and response-key rules with the organiser's final schema. Then connect the trained model artifact through the existing router interface when the other machine finishes.
2. Obtain the hidden-test input and generate predictions in the exact required CSV format. The local gold cases cannot substitute for that deliverable.
3. Have clinicians/domain mentors review temporal symptoms, negation, possible red flags and multilingual edge cases. Case G045 currently over-escalates historical chest pain (last year) during a routine-test request. This conservative false alarm remains explicit; emergency rules were not weakened to improve one metric.
4. Check Hindi/Hinglish speech on the target microphone, including denials and corrections. Automated tests use mocks and cannot establish real speech-recognition accuracy.
5. Produce the 2-page write-up and <=3-minute demo video; document all public training sources and model APIs. Add Docker only if needed for judging; it is preferred rather than mandatory.
6. Keep the prototype limits clear: demo location choices, in-memory bookings, no authentication/dispatch/payment workflow, no clinical diagnosis or prescriptions, and no production patient-data claim.
