# 10 — GPU run: multilingual adaptation then CareCompass LOFO

- multilingual-e5-base: stage A trained on 1779 complaints, held-out disease accuracy 1.000 (10 diseases)
- muril-base-cased: stage A trained on 1779 complaints, held-out disease accuracy 0.954 (10 diseases)
- xlm-roberta-base: stage A trained on 1779 complaints, held-out disease accuracy 0.944 (10 diseases)

Means over seeds; LOFO over 66 texts / 20 families.

| encoder | variant | mode | macro_f1 | accuracy | emergency_recall | over_triage |
|---|---|---|---|---|---|---|
| multilingual-e5-base | adapted | finetune | 0.518 | 0.576 | 0.63 | 5.667 |
| multilingual-e5-base | adapted | frozen | 0.632 | 0.682 | 0.444 | 4.0 |
| multilingual-e5-base | base | finetune | 0.603 | 0.636 | 0.778 | 5.667 |
| multilingual-e5-base | base | frozen | 0.641 | 0.667 | 0.667 | 5.0 |
| muril-base-cased | adapted | finetune | 0.219 | 0.313 | 1.0 | 24.333 |
| muril-base-cased | adapted | frozen | 0.402 | 0.47 | 0.778 | 7.0 |
| muril-base-cased | base | finetune | 0.056 | 0.152 | 1.0 | 52.333 |
| muril-base-cased | base | frozen | 0.551 | 0.561 | 0.778 | 3.0 |
| xlm-roberta-base | adapted | finetune | 0.529 | 0.53 | 1.0 | 3.667 |
| xlm-roberta-base | adapted | frozen | 0.359 | 0.379 | 0.333 | 3.0 |
| xlm-roberta-base | base | finetune | 0.318 | 0.359 | 1.0 | 17.0 |
| xlm-roberta-base | base | frozen | 0.511 | 0.515 | 0.556 | 6.0 |

## Decision rule

- multilingual-e5-base / finetune: adapted F1 0.518 vs base 0.603; recall 0.63 vs 0.778 -> **keep base**
- multilingual-e5-base / frozen: adapted F1 0.632 vs base 0.641; recall 0.444 vs 0.667 -> **keep base**
- muril-base-cased / finetune: adapted F1 0.219 vs base 0.056; recall 1.0 vs 1.0 -> **ADOPT**
- muril-base-cased / frozen: adapted F1 0.402 vs base 0.551; recall 0.778 vs 0.778 -> **keep base**
- xlm-roberta-base / finetune: adapted F1 0.529 vs base 0.318; recall 1.0 vs 1.0 -> **ADOPT**
- xlm-roberta-base / frozen: adapted F1 0.359 vs base 0.511; recall 0.333 vs 0.556 -> **keep base**

## What to do with this

1. Commit `pipeline/results/` and this report (small). Do NOT commit `pipeline/models_ft/` (weights).
2. Per the decision rule above, an ADOPT row means the adapted encoder is better on the 66-text LOFO. The deployment plan has no model weights at runtime, so use this only as a yardstick for the rules layer (see progress.md section 0).
3. Paste `pipeline/results/gpu_run_info.json` and this table into the next session so the assistant can update progress.md.
