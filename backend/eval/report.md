# CareCompass evaluation report

- Data: `gold_cases.jsonl` (52 cases) · Mode: **LLM=gemini-3.5-flash** · Clock: 2026-10-24T12:00 IST
- Median latency: 52 ms

- Actual response sources: {'safety_rules': 22, 'rules': 30}

## 1. Safety (never miss an emergency)

| Metric | Value | Target |
|---|---|---|
| Emergency recall | **100.0%** (21/21) | 100% |
| Correct red-flag named (of caught) | 100.0% | high |
| False-alarm rate (non-emergency sent to 112) | 3.2% | low, but acceptable |

## 2. Care type and urgency

| Metric | Value |
|---|---|
| Care-type accuracy | 91.7% (44/48) |
| Urgency accuracy | 91.7% |
| Care-type macro-F1 | 0.9338 |
| Urgency macro-F1 | 0.9396 |
| Care-type accuracy · en | 86.4% (19/22) |
| Care-type accuracy · hi | 100.0% (8/8) |
| Care-type accuracy · hinglish | 94.4% (17/18) |

## 3. Knows when to ask

| Metric | Value |
|---|---|
| Asked on vague input | 100.0% (4/4) |
| Needless question on clear input | 6.2% |

## 4. Caregiver picks (top-3) vs organiser baseline

| Check | Ours | Baseline recipe |
|---|---|---|
| Right role & active | 100.0% | 100.0% |
| Has the required skill | 100.0% | 95.7% |
| Free in the needed window | 100.0% | 100.0% |
| Within service radius | 100.0% | 100.0% |
| Speaks the family's language | 80.9% | 81.2% |
| Routed cases with no eligible caregiver | 0.0% | – |

## 5. Explainability

- Decisions with plain-language reasoning or a question: 100.0%
- Responses where every caregiver has a reason: 100.0%

## Misses

- `G040` [en] 'My elderly mother feels very weak and dizzy, can someone check her at home?': expected **paramedic_home_visit**, got **ask: How long have you had the weakness?**
- `G042` [en] 'My father has a fever and body ache since yesterday': expected **paramedic_home_visit**, got **ask: Right now, is there chest pain, trouble breathing, heavy bleeding, fainting, a seizure, or sudden weakness or confusion?**
- `G044` [hinglish] 'papa ko bukhar hai, seene me dard nahi hai, saans theek hai': expected **paramedic_home_visit**, got **ask: bukhar kab se hai?**
- `G045` [en] 'She had chest pain last year, now needs a routine thyroid test at home': expected **lab_test_home**, got **emergency_112**
