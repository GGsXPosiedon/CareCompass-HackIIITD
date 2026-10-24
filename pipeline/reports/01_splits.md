# 01 — Leakage-safe splits

## CareCompass: 3 grouped folds over 20 frozen scenario families

| fold | care_type | families | utterances | rows |
|---|---|---|---|---|
| A | <follow-up> | 2 | 6 | 19 |
| A | emergency_112 | 1 | 3 | 18 |
| A | home_nursing | 2 | 9 | 53 |
| A | lab_test_home | 1 | 3 | 18 |
| A | paramedic_home_visit | 1 | 3 | 11 |
| A | teleconsultation | 1 | 3 | 14 |
| B | <follow-up> | 1 | 3 | 11 |
| B | emergency_112 | 1 | 3 | 20 |
| B | home_nursing | 1 | 3 | 15 |
| B | lab_test_home | 1 | 3 | 17 |
| B | paramedic_home_visit | 1 | 3 | 17 |
| B | teleconsultation | 1 | 3 | 19 |
| C | <follow-up> | 1 | 3 | 9 |
| C | emergency_112 | 1 | 3 | 18 |
| C | home_nursing | 1 | 6 | 35 |
| C | lab_test_home | 1 | 3 | 16 |
| C | paramedic_home_visit | 1 | 3 | 15 |
| C | teleconsultation | 1 | 3 | 15 |

Leakage check: **PASS**

Reading these numbers: each fold's test scenarios are *unseen scenarios in all three languages*. Each fold has one emergency family, so emergency recall can only be read per scenario. Use the folds as regression tests, not as evidence of clinical safety.

## SYNAPSE: grouped by normalised `Symptoms` text

3,142 groups, 130,637 rows. Rows per split: {'test': 12261, 'train': 106302, 'val': 12074}; groups per split: {'test': 298, 'train': 2556, 'val': 288}. Severity is not used (no signal; see DATA_AUDIT §5.1).

## DDXPlus: duplicate patient signatures removed (priority test > validate > train)

| split | rows | dropped_within_split | dropped_cross_split | kept |
|---|---|---|---|---|
| test | 134529 | 270 | 0 | 134259 |
| validate | 132448 | 210 | 508 | 131730 |
| train | 1025602 | 27385 | 11521 | 986696 |
