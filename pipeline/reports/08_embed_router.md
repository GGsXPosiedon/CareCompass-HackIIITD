# 08 — Frozen multilingual-e5-base head: LOFO result and emergency thresholds

Features: `multilingual-e5-base` sentence embeddings (ONNX, CPU), logistic regression, care type: C=0.3 balanced; emergency score: separate binary head on standardised embeddings, C=0.03 balanced. Same 66 texts, 20 families and leave-one-family-out protocol as report 06.

| Model | Macro-F1 (95% family-bootstrap CI) | Accuracy | Emergency recall | Over-triage to 112 | Emergency AUROC |
|---|---|---|---|---|---|
| char n-gram (report 06, nested) | 0.416 (0.25–0.52) | 0.470 | 0.556 | 2 | 0.938 |
| **e5 head (this report)** | **0.680** (0.47–0.79) | 0.697 | 0.667 | 4 | 0.947 (binary head) |

Caveat: C was picked after looking at six e5 configurations on these same folds (all six beat the char baseline: F1 0.54–0.68), so the headline is optimistic; the gain over char n-grams is not.

## Emergency score sweep (LOFO, held-out family each time)

| tau | caught | missed | false alarms | recall | precision |
|---|---|---|---|---|---|
| 0.05 | 9 | 0 | 29 | 1.000 | 0.237 |
| 0.10 | 9 | 0 | 16 | 1.000 | 0.360 |
| 0.15 | 9 | 0 | 10 | 1.000 | 0.474 |
| 0.20 | 7 | 2 | 6 | 0.778 | 0.538 |
| 0.25 | 7 | 2 | 4 | 0.778 | 0.636 |
| 0.30 | 6 | 3 | 2 | 0.667 | 0.750 |
| 0.35 | 6 | 3 | 2 | 0.667 | 0.750 |
| 0.40 | 5 | 4 | 2 | 0.556 | 0.714 |
| 0.45 | 5 | 4 | 2 | 0.556 | 0.714 |
| 0.50 | 4 | 5 | 1 | 0.444 | 0.800 |
| 0.55 | 2 | 7 | 1 | 0.222 | 0.667 |
| 0.60 | 2 | 7 | 1 | 0.222 | 0.667 |
| 0.65 | 1 | 8 | 0 | 0.111 | 1.000 |
| 0.70 | 1 | 8 | 0 | 0.111 | 1.000 |
| 0.75 | 1 | 8 | 0 | 0.111 | 1.000 |
| 0.80 | 0 | 9 | 0 | 0.000 | nan |
| 0.85 | 0 | 9 | 0 | 0.000 | nan |
| 0.90 | 0 | 9 | 0 | 0.000 | nan |

**tau_ask = 0.15** (largest tau that still catches 9/9): a score at or above it asks one danger-sign question.
**tau_emergency = 0.65** (smallest tau with zero false alarms in LOFO): a score at or above it goes to the 112 path by itself.
Both come from held-out scores. With 9 emergency texts in 3 families the intervals are wide; the rules and the LLM stay in front of this score and it can only raise urgency.
