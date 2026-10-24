# 00 — Data inventory

Data root: `/sessions/rcw-01m3xkht9pko1bjimsveay6s/mnt/datasets`  ·  files: 12

| File | Bytes | Rows | Columns | SHA-256 | Notes |
|---|---:|---:|---|---|---|
| `SYNAPSE_An Expert Annotated Dataset of Patient symptoms and Demographics.csv` | 20,745,068 | 130,637 | Symptoms, Gender, Age, Duration, Severity, Final Recommendation | `3244475a5d2fbf0c…` |  |
| `all_craft_md.jsonl` | 245,479 | 140 | id, question, context, options, answer, answer_idx, facts, patient | `658441e6c6692c84…` |  |
| `all_dev_good.jsonl` | 2,585,822 | 1,272 | id, question, context, context_len, options, answer, answer_idx, explanation … | `3bfc7090d060dd8d…` |  |
| `caregivers.csv` | 10,613 | 60 | caregiver_id, name, role, qualification, gender, languages, skills, base_area … | `b38b6b81e41fe781…` |  |
| `ddx/ddx/release_conditions.json` | 20,889 | 49 | Spontaneous pneumothorax, Cluster headache, Boerhaave, Spontaneous rib fracture, GERD | `56edf4682d8e86a4…` |  |
| `ddx/ddx/release_evidences.json` | 120,263 | 223 | E_91, E_55, E_53, E_57, E_54 | `281c78b044ae6051…` |  |
| `ddx/ddx/release_test_patients.csv` | 88,717,003 | 134,529 | AGE, DIFFERENTIAL_DIAGNOSIS, SEX, PATHOLOGY, EVIDENCES, INITIAL_EVIDENCE | `b7bbc5e32b26ae49…` |  |
| `ddx/ddx/release_train_patients.csv` | 670,584,506 | 1,025,602 | AGE, DIFFERENTIAL_DIAGNOSIS, SEX, PATHOLOGY, EVIDENCES, INITIAL_EVIDENCE | `93933e9a9a7a00d6…` |  |
| `ddx/ddx/release_validate_patients.csv` | 87,371,169 | 132,448 | AGE, DIFFERENTIAL_DIAGNOSIS, SEX, PATHOLOGY, EVIDENCES, INITIAL_EVIDENCE | `b84733533bff01da…` |  |
| `multi_turn_examples.jsonl` | 1,044 | 2 | id, turns | `634a146457744f0d…` |  |
| `triage_dataset.jsonl` | 202,820 | 340 | id, detected_language, request, response | `51a157aa94d9d771…` |  |
| `triage_dataset_flat.csv` | 78,335 | 340 | id, detected_language, user_input, lat, lng, care_type, urgency, red_flags … | `1a567311c73aa1e1…` |  |

Full hashes are in `data/manifests/source_manifest.json`.
