# 09 — Multilingual medical symptom triage dataset: audit and derived assets

Source: `Tulsiandhare/Multilingual_medical_symptom_triage` (13923 rows -> 1976 unique complaints after removing the demographic header).

## Label audit (grouped 5-fold, char n-gram LR)

| Target | Accuracy | Majority baseline |
|---|---|---|
| disease | 1.000 | 0.170 |
| urgency | 0.348 | 0.366 |

`urgency` (= `severity`, identical up to renaming) is at chance: it is independent of disease, symptoms, age and comorbidities in the generator. It is therefore **not used** as an emergency/care label. `disease` is determined by the text (a 10-class task with 1.0 accuracy), so the dataset is used for multilingual symptom understanding, not for urgency.

## Language column vs real script of the complaint

```
lang      bengali  devanagari  english  gujarati  hinglish  telugu
language                                                          
English       404         407     2945       407         0     407
Hindi         390         405     2968       371         0     398
Hinglish      452         456        4       456      2997     456
```

## Derived symptom-cue vocabulary

232 tokens (lift >= 1.6, document frequency >= 15); by language: {'english': 12, 'devanagari': 61, 'telugu': 52, 'bengali': 51, 'gujarati': 56}.

Examples (highest lift per language):

- **bengali**: ক্লান্তি, প্রস্রাব, তৃষ্ণা, পেটে, দুর্বলতা, ঘনঘন, শরীর, বমি, ভাব, আলোর, প্রতি, সংবেদনশীলতা
- **devanagari**: तहान, वारंवार, थकवा, लघवी, अंगदुखी, पोटात, अशक्तपणा, नाकातून, वाहणे, पाणी, शिंक, नाक
- **english**: chills, sweating, joint, high, taste, loss, dry, wheezing, pain, headache, cough, fever
- **gujarati**: થાક, પેશાબ, વારંવાર, તરસ, શરીરમાં, નબળાઈ, પેટમાં, નાકમાંથી, વહેવું, પાણી, છીંક, જેવું
- **telugu**: మూత్రవిసర్జన, తరచుగా, అలసట, దాహం, శరీర, కడుపు, నొప్పులు, వికారం, కాంతి, సున్నితత్వం, వణుకు, చెమట
