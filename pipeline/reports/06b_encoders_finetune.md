# 06b — Pretrained encoders (LOFO, same protocol as 06_triage.md)

| model | mode | seed | macro_f1 | accuracy | emergency_recall | emergency_fn | over_triage | macro_f1_ci | seconds |
|---|---|---|---|---|---|---|---|---|---|
| intfloat/multilingual-e5-base | finetune | 0 | 0.6165065441381231 | 0.6515151515151515 | 0.6666666666666666 | 3 | 6 | 0.42-0.72 | 443 |
| intfloat/multilingual-e5-base | finetune | 1 | 0.6136011136011136 | 0.6363636363636364 | 0.7777777777777778 | 2 | 6 | 0.42-0.71 | 447 |
| intfloat/multilingual-e5-base | finetune | 2 | 0.577946127946128 | 0.6212121212121212 | 0.8888888888888888 | 1 | 5 | 0.40-0.67 | 450 |
| google/muril-base-cased | finetune | 0 | 0.04 | 0.13636363636363635 | 1.0 | 0 | 57 | 0.00-0.08 | 389 |
| google/muril-base-cased | finetune | 1 | 0.04 | 0.13636363636363635 | 1.0 | 0 | 57 | 0.00-0.08 | 393 |
| google/muril-base-cased | finetune | 2 | 0.08764186633039091 | 0.18181818181818182 | 1.0 | 0 | 43 | 0.03-0.13 | 397 |
| xlm-roberta-base | finetune | 0 | 0.28536414565826335 | 0.30303030303030304 | 1.0 | 0 | 12 | 0.14-0.40 | 474 |
| xlm-roberta-base | finetune | 1 | 0.23523873616662586 | 0.30303030303030304 | 1.0 | 0 | 23 | 0.11-0.35 | 478 |
| xlm-roberta-base | finetune | 2 | 0.43484023238925196 | 0.4696969696969697 | 1.0 | 0 | 16 | 0.27-0.54 | 481 |
