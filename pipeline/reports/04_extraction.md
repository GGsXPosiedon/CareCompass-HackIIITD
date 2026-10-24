# 04 — Multilingual symptom extraction (rule-based)

Registry `draft-0.1` (unreviewed; 32 concepts). No gold label here is clinician-reviewed.

## A. CareCompass utterances — IN-SAMPLE (66 unique texts)

The registry was written while reading these texts, so this measures cross-language consistency, not generalisation.

| Slice | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| English | 25 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Hindi | 25 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| Hinglish | 25 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| ALL | 75 | 0 | 0 | 1.00 | 1.00 | 1.00 |

Duration correct: 6/6.

## B. Adversarial set — 40 hand-written cases (negation, history, third party, Hinglish, noise)

Written by the same author in the same session as the lexicon; some variants (e.g. `nhi`, `breathlessness`) were added while writing it. A smoke test, not an independent benchmark. Cases tagged `oov` list only in-vocabulary concepts in their gold, so their score does not count the missed out-of-vocabulary symptoms (e.g. headache).

| Slice | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 60 | 0 | 3 | 1.00 | 0.95 | 0.98 |
| contradiction | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| duration | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| emergency | 8 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| empty | 0 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| history | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| hypothetical | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| mixed | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| negation | 24 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| noisy | 1 | 0 | 3 | 1.00 | 0.25 | 0.40 |
| oov | 1 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| persistence | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| request | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| spelling | 2 | 0 | 0 | 1.00 | 1.00 | 1.00 |
| third | 5 | 0 | 0 | 1.00 | 1.00 | 1.00 |

Experiencer correct: 19/19; duration correct: 8/8; clarification flag correct: 3/3.

## Failure cases

- `{"id": "a31", "text": "bukhr hai aur kasi", "tag": "noisy", "missed": [["cough", "present"], ["fever", "present"]], "unexpected": []}`
- `{"id": "a32", "text": "chst pain since morning", "tag": "noisy", "missed": [["chest_pain", "present"]], "unexpected": []}`

## Known limits

- Vocabulary-bound: unlisted symptoms (e.g. headache, vomiting) are not extracted; the result then sets `needs_clarification`, it never implies absence.
- No fuzzy matching: misspellings outside the listed variants are missed (see tag `noisy`).
- Negation, history and hypothetical cues are shallow window rules, not a parser.
- Extraction states what the text says; it assigns no care type, urgency or red-flag decision.
