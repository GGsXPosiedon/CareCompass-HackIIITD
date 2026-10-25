# CareCompass evaluation report

- Data: `gold_cases.jsonl` (52 cases) · Mode: **LLM off (rules only)** · Clock: 2026-10-24T12:00 IST
- Median latency: 8 ms

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
| Care-type accuracy | 81.2% (39/48) |
| Urgency accuracy | 81.2% |
| Care-type macro-F1 | 0.7800 |
| Urgency macro-F1 | 0.8833 |
| Care-type accuracy · en | 81.8% (18/22) |
| Care-type accuracy · hi | 87.5% (7/8) |
| Care-type accuracy · hinglish | 77.8% (14/18) |

## 3. Knows when to ask

| Metric | Value |
|---|---|
| Asked on vague input | 100.0% (4/4) |
| Needless question on clear input | 16.7% |

## 4. Caregiver picks (top-3) vs organiser baseline

| Check | Ours | Baseline recipe |
|---|---|---|
| Right role & active | 100.0% | 100.0% |
| Has the required skill | 100.0% | 94.4% |
| Free in the needed window | 100.0% | 100.0% |
| Within service radius | 100.0% | 100.0% |
| Speaks the family's language | 79.2% | 79.6% |
| Routed cases with no eligible caregiver | 0.0% | – |

## 5. Explainability

- Decisions with plain-language reasoning or a question: 100.0%
- Responses where every caregiver has a reason: 100.0%

## Misses

- `G038` [hinglish] 'papa ko do din se bukhar hai aur khansi bhi': expected **paramedic_home_visit**, got **ask: Kya saans lene mein taklif, uljhan ya bahut neend, gardan akadna, daura, hoth neele ya aisa daane hain jo dabane par nahi jaate?**
- `G039` [hi] 'पापा को दो दिन से बुखार और खांसी है': expected **paramedic_home_visit**, got **ask: क्या साँस लेने में तकलीफ़, उलझन या बहुत नींद, गर्दन अकड़ना, दौरा, नीले होंठ या दबाने पर न मिटने वाले दाने हैं?**
- `G040` [en] 'My elderly mother feels very weak and dizzy, can someone check her at home?': expected **paramedic_home_visit**, got **ask: Sudden weakness on one side, slurred speech, drooping face, fainting, or a fall with injury?**
- `G041` [hinglish] 'mummy ka bp sugar ghar pe check karwana hai': expected **paramedic_home_visit**, got **ask: Uljhan, behoshi, saans mein meethi gandh, ya high BP ke saath tez sir dard, seene mein dard, ek taraf kamzori?**
- `G042` [en] 'My father has a fever and body ache since yesterday': expected **paramedic_home_visit**, got **ask: Is there trouble breathing, confusion or unusual sleepiness, a stiff neck, a seizure, bluish lips, or a rash that does not fade when pressed?**
- `G043` [en] 'No chest pain, just a mild cough since two days, want someone to check at home': expected **paramedic_home_visit**, got **ask: Is the person struggling to breathe, unable to speak a full sentence, with blue lips, or chest pain?**
- `G044` [hinglish] 'papa ko bukhar hai, seene me dard nahi hai, saans theek hai': expected **paramedic_home_visit**, got **ask: Kya saans lene mein taklif, uljhan ya bahut neend, gardan akadna, daura, hoth neele ya aisa daane hain jo dabane par nahi jaate?**
- `G045` [en] 'She had chest pain last year, now needs a routine thyroid test at home': expected **lab_test_home**, got **emergency_112**
- `M001` [hinglish] 'mummy ko 2 din se bukhar hai, ghar pe dikhana hai': expected **paramedic_home_visit**, got **ask: Uljhan, behoshi, saans mein meethi gandh, ya high BP ke saath tez sir dard, seene mein dard, ek taraf kamzori?**
