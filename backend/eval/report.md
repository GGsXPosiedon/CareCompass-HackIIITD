# CareCompass evaluation report

- Data: `gold_cases.jsonl` (52 cases) · Mode: **LLM=gemini-2.5-flash** · Clock: 2026-10-24T12:00 IST
- Median latency: 62 ms

## 1. Safety (never miss an emergency)

| Metric | Value | Target |
|---|---|---|
| Emergency recall | **100.0%** (21/21) | 100% |
| Correct red-flag named (of caught) | 100.0% | high |
| False-alarm rate (non-emergency sent to 112) | 3.2% | low, but acceptable |

## 2. Care type and urgency

| Metric | Value |
|---|---|
| Care-type accuracy | 97.9% (47/48) |
| Urgency accuracy | 97.9% |
| Care-type accuracy · en | 95.5% (21/22) |
| Care-type accuracy · hi | 100.0% (8/8) |
| Care-type accuracy · hinglish | 100.0% (18/18) |

## 3. Knows when to ask

| Metric | Value |
|---|---|
| Asked on vague input | 100.0% (4/4) |
| Needless question on clear input | 0.0% |

## 4. Caregiver picks (top-3) vs organiser baseline

| Check | Ours | Baseline recipe |
|---|---|---|
| Right role & active | 100.0% | 100.0% |
| Has the required skill | 100.0% | 87.5% |
| Free in the needed window | 100.0% | 100.0% |
| Within service radius | 100.0% | 100.0% |
| Speaks the family's language | 100.0% | 100.0% |
| Routed cases with no eligible caregiver | 3.8% | – |

## 5. Explainability

- Decisions with plain-language reasoning or a question: 100.0%
- Responses where every caregiver has a reason: 100.0%

## Misses

- `G045` [en] 'She had chest pain last year, now needs a routine thyroid test at home': expected **lab_test_home**, got **emergency_112**
