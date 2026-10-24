# 06c — Emergency score threshold (tau = 0.1)

Rule under test: declare emergency when P(emergency | text) >= tau. Binary logistic regression, leave-one-family-out (each held-out emergency family is an unseen scenario), 9 emergency vs 57 other unique texts. Primary model fixed in advance: features `raw_char`, C=10, class_weight=balanced.

## At tau = 0.1

Recall 1.000 (9/9 emergencies caught, 0 missed), false alarms 39/57. Family-bootstrap 95% interval on recall: 1.00–1.00.

## Threshold sweep (primary model)

| tau | tp | fn | fp | recall | precision | fpr |
|---|---|---|---|---|---|---|
| 0.050 | 9 | 0 | 57 | 1.000 | 0.136 | 1.000 |
| 0.100 | 9 | 0 | 39 | 1.000 | 0.188 | 0.684 |
| 0.150 | 8 | 1 | 16 | 0.889 | 0.333 | 0.281 |
| 0.200 | 8 | 1 | 8 | 0.889 | 0.500 | 0.140 |
| 0.250 | 6 | 3 | 5 | 0.667 | 0.545 | 0.088 |
| 0.300 | 5 | 4 | 3 | 0.556 | 0.625 | 0.053 |
| 0.350 | 5 | 4 | 0 | 0.556 | 1.000 | 0.000 |
| 0.400 | 3 | 6 | 0 | 0.333 | 1.000 | 0.000 |
| 0.500 | 2 | 7 | 0 | 0.222 | 1.000 | 0.000 |
| 0.600 | 1 | 8 | 0 | 0.111 | 1.000 | 0.000 |
| 0.700 | 0 | 9 | 0 | 0.000 | nan | 0.000 |
| 0.800 | 0 | 9 | 0 | 0.000 | nan | 0.000 |

Reading it: the score ranks emergencies well (see AUROC below). Lowering tau trades missed emergencies for false alarms: compare the rows above. A tau chosen on these same folds is optimistic, and a probability like this has no absolute meaning: it depends on regularisation and class weighting (rows below), so re-pick tau whenever the model changes.

## Score of each emergency family (min / mean / max over its texts)

| family | label | min | mean | max |
|---|---|---|---|---|
| E1 | emergency_112 | 0.238 | 0.432 | 0.669 |
| E2 | emergency_112 | 0.214 | 0.407 | 0.515 |
| E3 | emergency_112 | 0.147 | 0.265 | 0.375 |

## All configurations at tau = 0.1

| features | C | weight | auroc | pr_auc | mean_p_emerg | mean_p_other | recall | fn | fp |
|---|---|---|---|---|---|---|---|---|---|
| raw_char | 100.000 | balanced | 0.938 | 0.784 | 0.308 | 0.046 | 0.778 | 2 | 6 |
| raw_char | 10.000 | balanced | 0.936 | 0.780 | 0.368 | 0.137 | 1.000 | 0 | 39 |
| raw+roman+words | 100.000 | balanced | 0.932 | 0.737 | 0.285 | 0.028 | 0.556 | 4 | 5 |
| raw_char | 100.000 | none | 0.926 | 0.767 | 0.158 | 0.023 | 0.556 | 4 | 2 |
| raw+roman+words | 10.000 | balanced | 0.922 | 0.702 | 0.317 | 0.077 | 0.778 | 2 | 9 |
| raw+roman_char | 10.000 | balanced | 0.922 | 0.744 | 0.361 | 0.094 | 0.889 | 1 | 18 |
| raw+roman_char | 100.000 | balanced | 0.922 | 0.748 | 0.330 | 0.033 | 0.667 | 3 | 5 |
| raw+roman_char | 100.000 | none | 0.918 | 0.742 | 0.181 | 0.017 | 0.444 | 5 | 1 |
| roman_char | 100.000 | balanced | 0.914 | 0.723 | 0.354 | 0.046 | 0.667 | 3 | 6 |
| raw+roman_char | 1.000 | balanced | 0.914 | 0.737 | 0.427 | 0.256 | 1.000 | 0 | 57 |
| raw_char | 1.000 | balanced | 0.910 | 0.756 | 0.445 | 0.336 | 1.000 | 0 | 57 |
| raw+roman+words | 100.000 | none | 0.908 | 0.681 | 0.152 | 0.015 | 0.444 | 5 | 1 |
| roman_char | 10.000 | balanced | 0.908 | 0.717 | 0.388 | 0.127 | 1.000 | 0 | 32 |
| raw+roman+words | 1.000 | balanced | 0.904 | 0.693 | 0.392 | 0.219 | 1.000 | 0 | 57 |
| roman_char | 100.000 | none | 0.901 | 0.703 | 0.204 | 0.024 | 0.444 | 5 | 3 |
| raw+roman_char | 10.000 | none | 0.899 | 0.713 | 0.173 | 0.048 | 0.556 | 4 | 5 |
| raw_char | 10.000 | none | 0.897 | 0.702 | 0.159 | 0.068 | 0.667 | 3 | 8 |
| raw+roman+words | 10.000 | none | 0.893 | 0.660 | 0.151 | 0.039 | 0.444 | 5 | 5 |
| roman_char | 1.000 | balanced | 0.887 | 0.713 | 0.451 | 0.312 | 1.000 | 0 | 57 |
| roman_char | 10.000 | none | 0.867 | 0.671 | 0.181 | 0.063 | 0.667 | 3 | 7 |
| raw+roman+words | 1.000 | none | 0.780 | 0.536 | 0.146 | 0.100 | 0.667 | 3 | 23 |
| text+concepts* | 100.000 | balanced | 0.764 | 0.281 | 0.040 | 0.021 | 0.222 | 7 | 4 |
| raw+roman_char | 1.000 | none | 0.749 | 0.546 | 0.147 | 0.112 | 0.889 | 1 | 38 |
| text+concepts* | 100.000 | none | 0.710 | 0.251 | 0.021 | 0.013 | 0.000 | 9 | 2 |
| text+concepts* | 10.000 | balanced | 0.690 | 0.232 | 0.067 | 0.053 | 0.222 | 7 | 5 |
| text+concepts* | 1.000 | balanced | 0.635 | 0.208 | 0.168 | 0.152 | 0.889 | 1 | 48 |
| text+concepts* | 10.000 | none | 0.622 | 0.199 | 0.028 | 0.027 | 0.000 | 9 | 4 |
| roman_char | 1.000 | none | 0.591 | 0.356 | 0.136 | 0.126 | 0.889 | 1 | 55 |
| text+concepts* | 1.000 | none | 0.481 | 0.154 | 0.069 | 0.075 | 0.222 | 7 | 8 |
| concepts_only* | 100.000 | balanced | 0.392 | 0.145 | 0.010 | 0.028 | 0.000 | 9 | 4 |
| raw_char | 1.000 | none | 0.370 | 0.122 | 0.123 | 0.131 | 0.889 | 1 | 57 |
| concepts_only* | 100.000 | none | 0.363 | 0.140 | 0.005 | 0.019 | 0.000 | 9 | 4 |
| concepts_only* | 10.000 | balanced | 0.298 | 0.126 | 0.033 | 0.074 | 0.000 | 9 | 12 |
| concepts_only* | 1.000 | balanced | 0.263 | 0.120 | 0.131 | 0.197 | 0.667 | 3 | 54 |
| concepts_only* | 10.000 | none | 0.251 | 0.118 | 0.015 | 0.038 | 0.000 | 9 | 4 |
| concepts_only* | 1.000 | none | 0.105 | 0.101 | 0.054 | 0.095 | 0.000 | 9 | 15 |

`auroc`/`pr_auc` are threshold-free. `weight=none` shrinks scores and makes high-ish thresholds unreachable; `balanced` inflates them. Neither is 'calibrated': 66 texts are too few to calibrate probabilities.

## Safety note

A learned score is never the only emergency path. Stage 5's hard-rule check runs first and cannot be cancelled by a low score; this detector only adds recall on top of it.
