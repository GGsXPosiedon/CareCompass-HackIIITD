# 03 — Harmonization

Label mapping: `interim-csv-v0.1` (interim team decision, not organizer-approved).

| Source | Rows in | Cases out | Notes |
|---|---:|---:|---|
| CareCompass | 340 | 340 | flags {'red_flags_quarantined_unreviewed': 56, 'no_routing_label_follow_up_expected': 39}; empty cells {'care_type': 39, 'urgency': 39, 'red_flags': 284, 'follow_up_question': 301, 'matched_caregiver_ids': 131, 'top_score': 131} |
| Caregivers | 60 | 60 | inactive 8 |
| SYNAPSE | 130637 | 130637 | splits {'train': 106302, 'val': 12074, 'test': 12261}; severity/recommendation kept as source labels only |
| DDXPlus (sample) | – | 6000 | 2000/split after dedupe; tokens 120,664, unresolved 0, recorded-No answers not modelled 6923, absent facts 0 |

Outputs are in `data/processed/` (git-ignored; regenerate with `python -m ccpipe.cli harmonize`).
Red flags from the CSV are kept verbatim in `source_labels.red_flags_raw`, flagged `red_flags_quarantined_unreviewed`, and never copied into `approved_labels`.
