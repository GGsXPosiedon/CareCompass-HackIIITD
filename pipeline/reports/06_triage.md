# 06 — Triage classification: feature-engineered baselines

Data: 66 unique texts (340 rows, the rest are the same text with different coordinates) in 20 scenario families; classes = 5 care types + `ask_followup` (rows with no label and a follow-up question). Labels are the interim CSV vocabulary (not organizer-approved).

**Protocol.** Leave-one-family-out (LOFO): every test text comes from a scenario family never seen in training, in any language. Model/feature choice is made by an inner LOFO inside each training set (nested), selecting lexicographically on emergency recall, then macro-F1. 95% intervals resample whole families (cluster bootstrap, 2000×). With 20 families the intervals are wide; treat everything here as a regression test, not as evidence of clinical safety.

## Headline (nested LOFO, honest estimate)

| Model family | Macro-F1 (95% CI) | Accuracy (95% CI) | Emergency recall | Emergency FN / 9 | Over-triage to 112 |
|---|---|---|---:|---:|---:|
| Majority class | 0.071 | 0.273 | 0.000 | 9 | 0 |
| Text features only | 0.416 (0.25–0.52) | 0.470 (0.28–0.65) | 0.556 | 4 | 2 |
| Text + concept features* | 0.427 (0.28–0.51) | 0.485 (0.32–0.65) | 0.667 | 3 | 2 |

\* The concept registry was written while reading these same utterances, so any configuration containing concept features is optimistic. Only the text-only row is free of that contamination.

## All configurations, plain LOFO (selection-biased, for comparison only)

| features | clf | macro_f1 | accuracy | emergency_recall | emergency_fn | over_triage |
|---|---|---|---|---|---|---|
| raw_char | cnb | 0.443 | 0.500 | 0.778 | 2 | 2 |
| raw+roman_char | cnb | 0.382 | 0.439 | 0.778 | 2 | 3 |
| text+concepts* | cnb | 0.606 | 0.667 | 0.667 | 3 | 3 |
| raw_char | svm_c1 | 0.390 | 0.424 | 0.667 | 3 | 2 |
| raw+roman_char | svm_c1 | 0.378 | 0.439 | 0.667 | 3 | 3 |
| raw_char | lr_c1 | 0.377 | 0.409 | 0.667 | 3 | 4 |
| raw+roman+words | cnb | 0.371 | 0.439 | 0.667 | 3 | 4 |
| raw_char | lr_c10 | 0.367 | 0.409 | 0.667 | 3 | 3 |
| roman_char | cnb | 0.320 | 0.394 | 0.667 | 3 | 5 |
| roman_char | svm_c1 | 0.347 | 0.394 | 0.556 | 4 | 4 |
| roman_char | lr_c1 | 0.335 | 0.364 | 0.556 | 4 | 3 |
| raw+roman_char | lr_c1 | 0.335 | 0.364 | 0.556 | 4 | 3 |
| raw_char | 1nn | 0.486 | 0.500 | 0.444 | 5 | 3 |
| roman_char | 1nn | 0.465 | 0.470 | 0.444 | 5 | 4 |
| raw+roman_char | 1nn | 0.457 | 0.470 | 0.444 | 5 | 4 |
| raw+roman+words | svm_c1 | 0.345 | 0.394 | 0.444 | 5 | 3 |
| raw+roman+words | lr_c10 | 0.343 | 0.394 | 0.444 | 5 | 3 |
| raw+roman+words | lr_c1 | 0.333 | 0.364 | 0.444 | 5 | 3 |
| roman_char | lr_c10 | 0.328 | 0.364 | 0.444 | 5 | 3 |
| raw+roman_char | lr_c10 | 0.328 | 0.364 | 0.444 | 5 | 3 |
| concepts_only* | cnb | 0.749 | 0.803 | 0.333 | 6 | 4 |
| concepts_only* | 1nn | 0.523 | 0.576 | 0.333 | 6 | 7 |
| raw+roman+words | 1nn | 0.458 | 0.470 | 0.333 | 6 | 3 |
| text+concepts* | svm_c1 | 0.574 | 0.636 | 0.222 | 7 | 2 |
| text+concepts* | lr_c1 | 0.531 | 0.591 | 0.222 | 7 | 3 |
| text+concepts* | 1nn | 0.526 | 0.561 | 0.222 | 7 | 2 |
| text+concepts* | lr_c10 | 0.513 | 0.576 | 0.222 | 7 | 3 |
| concepts_only* | lr_c1 | 0.511 | 0.606 | 0.000 | 9 | 3 |
| concepts_only* | lr_c10 | 0.472 | 0.576 | 0.000 | 9 | 0 |
| concepts_only* | svm_c1 | 0.432 | 0.530 | 0.000 | 9 | 0 |

## Repeated grouped 3-fold CV (10 random family partitions, modal config `raw_char|cnb`)

Macro-F1 mean 0.468 (min 0.422, max 0.535); emergency recall mean 0.722 (min 0.667); emergency FN per partition [2, 3, 2, 3, 3, 3, 3, 2, 2, 2]. The spread shows how much the choice of family partition moves the result.

## Approved folds A/B/C (modal config)

| fold | macro_f1 | accuracy | emergency_recall | emergency_fn | over_triage |
|---|---|---|---|---|---|
| A | 0.703 | 0.704 | 1.000 | 0 | 2 |
| B | 0.378 | 0.444 | 0.667 | 1 | 3 |
| C | 0.511 | 0.619 | 0.667 | 1 | 0 |

## Per-family result (nested LOFO, text + concepts)

| family | label | n | correct |
|---|---|---|---|
| E1 | emergency_112 | 3 | 2 |
| E2 | emergency_112 | 3 | 2 |
| E3 | emergency_112 | 3 | 2 |
| F1 | ask_followup | 3 | 0 |
| F2 | ask_followup | 3 | 1 |
| F3 | ask_followup | 3 | 2 |
| F4 | ask_followup | 3 | 0 |
| L1 | lab_test_home | 3 | 1 |
| L2 | lab_test_home | 3 | 1 |
| L3 | lab_test_home | 3 | 3 |
| N1 | home_nursing | 6 | 4 |
| N2 | home_nursing | 3 | 3 |
| N3 | home_nursing | 6 | 6 |
| N4 | home_nursing | 3 | 3 |
| P1 | paramedic_home_visit | 3 | 0 |
| P2 | paramedic_home_visit | 3 | 1 |
| P3 | paramedic_home_visit | 3 | 0 |
| T1 | teleconsultation | 3 | 1 |
| T2 | teleconsultation | 3 | 0 |
| T3 | teleconsultation | 3 | 0 |

## Confusion matrix (nested LOFO, text + concepts)

| true | emergency_112 | home_nursing | lab_test_home | paramedic_home_visit | teleconsultation | ask_followup |
|---|---|---|---|---|---|---|
| emergency_112 | 6 | 1 | 0 | 2 | 0 | 0 |
| home_nursing | 0 | 16 | 0 | 0 | 1 | 1 |
| lab_test_home | 0 | 0 | 5 | 4 | 0 | 0 |
| paramedic_home_visit | 1 | 2 | 4 | 1 | 0 | 1 |
| teleconsultation | 0 | 1 | 0 | 0 | 1 | 7 |
| ask_followup | 1 | 2 | 0 | 3 | 3 | 3 |

## Confusion matrix (nested LOFO, text only)

| true | emergency_112 | home_nursing | lab_test_home | paramedic_home_visit | teleconsultation | ask_followup |
|---|---|---|---|---|---|---|
| emergency_112 | 5 | 1 | 0 | 3 | 0 | 0 |
| home_nursing | 0 | 16 | 0 | 0 | 1 | 1 |
| lab_test_home | 0 | 0 | 5 | 4 | 0 | 0 |
| paramedic_home_visit | 1 | 2 | 3 | 1 | 0 | 2 |
| teleconsultation | 0 | 1 | 0 | 0 | 1 | 7 |
| ask_followup | 1 | 2 | 0 | 3 | 3 | 3 |

## Per-language accuracy (nested, text + concepts)

{"English": 0.36363636363636365, "Hindi": 0.5454545454545454, "Hinglish": 0.5454545454545454}

## Urgency

In this dataset urgency is a function of care type: True. So urgency is derived from the predicted care type through the taxonomy pair rules rather than modelled separately (derived-urgency exact match 0.545). A separate urgency model would only re-learn care type and cannot be validated independently here.

## Latency (single text, CPU)

p50 0.59 ms, p95 0.86 ms.

## Misclassified texts (nested LOFO, text only)

- [E2/English] `Heavy bleeding that won't stop after an accident` → true `emergency_112`, predicted `home_nursing`
- [E3/English] `My father is having severe chest pain and can't breathe` → true `emergency_112`, predicted `paramedic_home_visit`
- [E3/Hinglish] `papa ko severe chest pain hai saans nahi aa rahi` → true `emergency_112`, predicted `paramedic_home_visit`
- [E3/Hindi] `पापा को तेज सीने में दर्द है और सांस नहीं आ रही` → true `emergency_112`, predicted `paramedic_home_visit`
- [F1/English] `Doctor chahiye` → true `ask_followup`, predicted `teleconsultation`
- [F1/Hinglish] `doctor chahiye` → true `ask_followup`, predicted `teleconsultation`
- [F1/Hindi] `डॉक्टर चाहिए` → true `ask_followup`, predicted `teleconsultation`
- [F2/English] `Hi, is anyone there?` → true `ask_followup`, predicted `emergency_112`
- [F2/Hindi] `नमस्ते, कोई है?` → true `ask_followup`, predicted `home_nursing`
- [F3/English] `I need help` → true `ask_followup`, predicted `home_nursing`
- [F4/English] `I want to book something for my mother` → true `ask_followup`, predicted `paramedic_home_visit`
- [F4/Hinglish] `mummy ke liye kuch book karna hai` → true `ask_followup`, predicted `paramedic_home_visit`
- [F4/Hindi] `माँ के लिए कुछ बुक करना है` → true `ask_followup`, predicted `paramedic_home_visit`
- [L1/English] `Book a full body checkup, home collection` → true `lab_test_home`, predicted `paramedic_home_visit`
- [L1/Hinglish] `full body checkup home collection` → true `lab_test_home`, predicted `paramedic_home_visit`
- [L2/English] `Need blood sugar test at home tomorrow morning` → true `lab_test_home`, predicted `paramedic_home_visit`
- [L2/Hinglish] `kal subah sugar test ghar pe` → true `lab_test_home`, predicted `paramedic_home_visit`
- [N1/English] `Doctor prescribed an injection, can someone come home` → true `home_nursing`, predicted `teleconsultation`
- [N1/Hindi] `डॉक्टर ने इंजेक्शन लिखा है, घर कोई आ सकता है` → true `home_nursing`, predicted `ask_followup`
- [P1/English] `Grandfather is weak and not eating, want a home check-up` → true `paramedic_home_visit`, predicted `emergency_112`
- [P1/Hinglish] `dadaji weak hain, ghar pe checkup chahiye` → true `paramedic_home_visit`, predicted `ask_followup`
- [P1/Hindi] `दादाजी कमजोर हैं, घर पर जांच चाहिए` → true `paramedic_home_visit`, predicted `ask_followup`
- [P2/Hinglish] `papa ko do din se bukhar hai aur khansi bhi` → true `paramedic_home_visit`, predicted `home_nursing`
- [P2/Hindi] `पापा को दो दिन से बुखार और खांसी है` → true `paramedic_home_visit`, predicted `home_nursing`
- [P3/English] `Need someone to check BP and sugar at home for my mother` → true `paramedic_home_visit`, predicted `lab_test_home`
- [P3/Hinglish] `mummy ka bp sugar ghar pe check karwana hai` → true `paramedic_home_visit`, predicted `lab_test_home`
- [P3/Hindi] `माँ का बीपी और शुगर घर पर चेक करवाना है` → true `paramedic_home_visit`, predicted `lab_test_home`
- [T1/Hinglish] `subah se acidity gas hai, doctor se consult karna hai` → true `teleconsultation`, predicted `ask_followup`
- [T1/Hindi] `सुबह से एसिडिटी है, डॉक्टर से सलाह चाहिए` → true `teleconsultation`, predicted `ask_followup`
- [T2/English] `Need a second opinion on my child's prescription` → true `teleconsultation`, predicted `home_nursing`
- [T2/Hinglish] `bacche ki medicine pe second opinion chahiye` → true `teleconsultation`, predicted `ask_followup`
- [T2/Hindi] `बच्चे की दवा पर सेकंड ओपिनियन चाहिए` → true `teleconsultation`, predicted `ask_followup`
- [T3/English] `Want to talk to a doctor about my reports` → true `teleconsultation`, predicted `ask_followup`
- [T3/Hinglish] `reports ke baare me doctor se baat karni hai` → true `teleconsultation`, predicted `ask_followup`
- [T3/Hindi] `रिपोर्ट के बारे में डॉक्टर से बात करनी है` → true `teleconsultation`, predicted `ask_followup`

## Not done / blocked

- Pretrained multilingual encoders (e5, BGE-M3, MuRIL, XLM-R, …) could not be run: this workspace has no GPU and cannot reach Hugging Face. See `scripts/gpu_encoder_eval.py` (runs the same LOFO protocol on your GPU machine).
- Safety: emergency handling must not rely on this classifier; Stage 5 defines the hard-rule path.
