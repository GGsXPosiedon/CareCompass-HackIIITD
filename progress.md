# CareCompass — intent / triage engine: current state

This file is overwritten on every update (latest architecture and results only). Last updated 2026-10-25.
Every number comes from a script in `pipeline/scripts/` and a report in `pipeline/reports/`. The assistant commits nothing.

## 0. Product direction (decided 2026-10-25) and what it changes

- **Deployment rule: no model weights at runtime.** The LLM chat handles intent, mood and conversation. Underneath it sits a **deterministic layer** (rules, lexicons, question trees, fixed disposition levels, small JSON tables) for Indian users, Delhi first, in the spirit of NHS 111: fixed pathways, fixed dispositions (112 / same-day / 1-2 days / self-care), every outcome explained by the rule or answer that caused it.
- The e5 / MuRIL / XLM-R work is therefore **offline tooling**: it builds and checks the deterministic assets and measures how far rules lag a learned model. `ROUTER_BACKEND=trained` stays available but is not the deployment target; `rules` is.
- **Negative result (scripts/distill_lexical.py):** distilling the e5 head into a runtime-free lexical model (word + char n-grams, JSON weights) does not work with the data we have: LOFO macro-F1 0.35-0.36 vs 0.68 for the e5 teacher (0.416 plain char n-grams). The unlabeled pools (symptom complaints) carry no care-type signal, so there is nothing for the student to copy. Care-type logic for deployment must come from pathway content (clinical sources + doctor review), not from fitting these 66 texts.
- Clinical content sources: public Indian/WHO protocols plus the datasets we hold; a clinician you know signs off. Delhi scope: localities and PIN codes, seasonal patterns (dengue, pollution, heat, winter respiratory), emergency numbers and facilities, plus Hindi/Hinglish/English wording.

### Decisions confirmed by the owner (2026-10-25, last session on the GPU-less handoff)
Dataset may be used to guess unknowns; LLM may reword; keep the current API/urgency interface (emergency / same_day / scheduled) and add **self-care advice** inside the response text only when it has backing; demo build may ship **unreviewed** content (marked); cover all caregiver areas (18 in `caregivers.csv`); mood should guess anger/panic/anxiety and route accordingly; strict thresholds for infants, pregnancy, children, elderly; converge in 4 questions (more only if the user cannot answer); briefcase NOT used yet; languages: English, Hindi, Hinglish; LLM translation of missing Hindi/Hinglish names is approved (reviewable file).

### New deterministic modules (built in the last session; unit-tested, NOT yet wired into the graph)
- `backend/app/rules/pathways.json` (+ generator `pipeline/scripts/build_pathways.py`): 7 pathways (fever, cough/breathing, vomiting/diarrhoea, chest pain, injury/wound, diabetes/BP, weakness/dizziness), 2-4 questions each in en/hinglish/hi, rules -> emergency / urgent / routine / self_care, strictness table, "unsure on a danger question = yes". **UNREVIEWED.**
- `backend/app/services/pathways.py`: `select(text)`, `evaluate(pid, answers, age_years, pregnant, lang)`, `parse_answer(...)`.
- `backend/app/services/mood.py`: panic / anger / anxiety cues -> danger-first, unsure=yes, max 1 question, human call-back, tone hint. Can only add caution.
- `backend/app/rules/delhi.json` (+ `pipeline/scripts/build_delhi_assets.py`): 18 service areas from caregivers.csv with aliases, emergency numbers (unverified), seasonal notes (unreviewed).
- Tests: `backend/tests/test_pathways.py` (10), `test_encoder_router.py` (13).

## 1. Architecture (request flow)

```
intake -> rules_safety -> +-- classify   (trained slot: rules, then e5 head)
                          +-- llm_safety
                          +-- llm_triage
                       -> fuse (+ emergency score) -> follow_up (<= 2-4 questions) | match caregivers -> respond
```

| Layer | File | Notes |
|---|---|---|
| Rules safety: 9 official red flags + explicit "ambulance / 112 / emergency" (EN/Hindi/Hinglish) | `backend/app/services/safety.py`, `app/rules/redflags.json` | always in front; false alarms accepted, misses are not |
| Intent gate / dialogue (greeting, general, health, named condition, refusal, stop...) | `services/dialogue.py`, `conditions.py`, `lexicon.py` | health cue = lexicon, unwell phrases, **dataset vocabulary** (new) |
| Trained care-type router | `services/routing.py::TrainedRouter`, `services/encoder_models.py`, `app/models/router_e5_lr.json` | ACTIVE (`ROUTER_BACKEND=trained`); rules first, e5 head when rules < 0.75 confident |
| Emergency score + danger-sign question | `encoder_models.py`, `graph/nodes.py` | score can only raise caution: ask once at >= 0.15, go to 112 at >= 0.65 |
| Dataset vocabulary | `backend/app/rules/dataset_vocab.json` (generated) | 232 symptom cues, 4 Indian scripts; deterministic, no model |
| Ambiguity question | `follow_up.ambiguity_question`, `graph/nodes.py::fuse`, `calibrate_ambiguity.py` | when the trained head cannot separate two care types (log-ratio < 0.0181, from LOFO), ask one two-option question; uses a free question slot. Needs the encoder, so it is off in a no-weights deployment |
| LLM intent fallback | `services/intent_llm.py`, `converse` | only widens `general` to `health` when an LLM says so with confidence >= medium; rules run first and are never lowered |

The encoder never lowers a rules or LLM decision. The RED_FLAGS enum is part of the API schema and is unchanged.

## 2. Datasets and how each one is used

| Dataset | Size | Used for | NOT used for |
|---|---|---|---|
| CareCompass gold (`carecompass`) | 66 unique texts, 20 scenario families | the only real care-type + urgency labels: trains the heads, all LOFO numbers | - |
| `Tulsiandhare/Multilingual_medical_symptom_triage` | 13,923 rows -> 1,976 unique complaints, 7 scripts | (a) symptom vocabulary for the intent gate, (b) stage A of the GPU fine-tune (name the disease), (c) multilingual evaluation of the gate | **urgency / severity / recommended_action as labels** (see below) |
| SYNAPSE | 2,034 symptom phrases | symptom lexicon (English) | - |
| DDXPlus | 49 conditions (severity 1-5), 223 evidences | planned: follow-up question selection and an auxiliary risk prior (approved) | care-type labels |
| MediQ | - | dialogue/follow-up behaviour reference | - |

**Audit of the external dataset (`pipeline/reports/09_multilingual_dataset.md`):**
- `urgency` and `severity` are the same label (Low/Medium/High = Mild/Moderate/Severe). They are independent of disease, symptoms, age and comorbidities: a grouped 5-fold char n-gram classifier scores **0.348 vs 0.366 majority** on urgency, while it scores **1.000** on disease. The generator assigned urgency at random, so training an emergency detector on it would teach the model that "fever, joint pain" is an emergency one time in three.
- The `language` column is wrong for most rows ("English" rows contain Telugu, Marathi, Gujarati...), so the real language is detected from the script.
- Only 10 diseases, template sentences (1,976 distinct complaints), Maharashtra regions. It is synthetic and rule-labelled by its own README. Delhi-specific signal has to come from elsewhere (caregivers.csv, gold set).
- Used correctly it still gives multilingual symptom wording for free: e.g. Devanagari तहान/थकवा, Bengali তৃষ্ণা/ক্লান্তি, Telugu అలసట/దాహం, Gujarati તરસ/થાક are all derived from the data, not typed by hand.
- Limit: Latin-script Hinglish in this dataset reuses English symptom words (40 distinct Hinglish complaints), so it adds little Hinglish vocabulary. Hinglish disease names (bukhar, khansi...) still come from the curated lexicon.

## 3. How the models were trained (CPU, already done)

- **Encoder:** `multilingual-e5-base`, ONNX int8, onnxruntime + tokenizers (no torch). Prefix `query: `, mean pool, L2 norm, max length 64.
- **Care-type head:** multinomial logistic regression, C=0.3, class_weight=balanced.
- **Emergency head:** separate binary logistic regression on standardised embeddings, C=0.03, balanced. (A single multinomial head squeezed the emergency probability so no threshold worked.)
- **Protocol:** leave-one-family-out over 20 families; thresholds read from held-out scores; family-bootstrap 95% CIs.

| Model | Macro-F1 | Accuracy | Emergency recall | Over-triage | Emergency AUROC |
|---|---|---|---|---|---|
| char n-gram baseline | 0.416 | 0.470 | 0.556 | 2 | 0.938 |
| e5 frozen head | **0.680** (0.47-0.79) | 0.697 | 0.667 | 4 | 0.947 |

End-to-end gold check in trained mode: emergency recall 21/21, care-type accuracy 91.7%. Test suite: 272 passed, 1 skipped (3 older tests that depend on the commented-out Gemini banner are deselected; not caused by this work).

## 3b. GPU fine-tuning: what was run and what it achieved (2026-10-25, RTX 4060 Laptop, torch 2.11+cu128, transformers 5.20.2)

**Run:** `run_gpu_windows.ps1`: (1) dataset audit, (2) baseline frozen and fine-tuned encoders on the 66 CareCompass texts, (3) two-stage run: Stage A teaches each encoder to name the disease from 1,779 multilingual complaints (7 scripts), Stage B re-tests on CareCompass, leave-one-family-out. Fixed recipe, never tuned: Stage A 2 epochs, lr 2e-5, batch 32; Stage B 12 epochs, lr 3e-5, batch 16, emergency class weight x3, 3 seeds. Raw files: `pipeline/results/*`, reports `06b_*`, `10_gpu_multilingual.md`.

| Encoder | Variant | Mode | Macro-F1 | Emergency recall | Over-triage (of 57) |
|---|---|---|---|---|---|
| e5-base | base | frozen + LR | **0.641** | 0.667 | 5 |
| e5-base | adapted (stage A) | frozen + LR | 0.632 | 0.444 | 4 |
| e5-base | base | fine-tuned | 0.603 | 0.778 | 5.7 |
| e5-base | adapted | fine-tuned | 0.518 | 0.630 | 5.7 |
| MuRIL | base | frozen | 0.551 | 0.778 | 3 |
| MuRIL | adapted | frozen | 0.402 | 0.778 | 7 |
| MuRIL | base / adapted | fine-tuned | 0.056 / 0.219 | 1.0 / 1.0 | 52 / 24 |
| XLM-R | base | frozen | 0.511 | 0.556 | 6 |
| XLM-R | adapted | frozen | 0.359 | 0.333 | 3 |
| XLM-R | base / adapted | fine-tuned | 0.318 / 0.529 | 1.0 / 1.0 | 17 / 3.7 |

Reference (CPU, shipped heads): e5 frozen head macro-F1 0.680 (optimistic, C tuned on the same folds); char n-grams 0.416.

**What was achieved**
1. **Stage A worked as a learning task**: held-out disease accuracy e5 1.000, MuRIL 0.954, XLM-R 0.944. The encoders do map Hindi/Hinglish/Marathi/Bengali/Telugu/Gujarati symptom wording onto shared disease concepts.
2. **It did not transfer to care-type or emergency routing.** Adapted e5 frozen: F1 0.632 vs 0.641 (no gain) and emergency recall fell 0.667 -> 0.444. Adapted MuRIL/XLM-R frozen are worse than their bases. Reason: the external data teaches *what illness*, while our labels are *which service and how urgent*; the two are nearly unrelated.
3. **Full fine-tuning on 57-60 training texts per fold is unstable and should not be used.** MuRIL base collapses to "everything is an emergency" (recall 1.0 but 52 of 57 false alarms, F1 0.056). XLM-R fine-tuned swings 0.24-0.43 across seeds. e5 fine-tuned (0.60) stays below e5 frozen (0.64). The x3 emergency weight with so little data pushes models to over-call 112.
4. **The script's "ADOPT" rows (MuRIL, XLM-R fine-tuned) are not real wins**: they only improve on a collapsed baseline and stay below the frozen e5 head (0.64-0.68). Do not adopt them.
5. **Ranking by this evidence:** frozen e5 + logistic head (0.64-0.68) > e5 fine-tuned (0.60) > MuRIL frozen (0.55) > XLM-R frozen (0.51). Nothing beat the e5 head already in `backend/app/models/router_e5_lr.json`. XLM-R adapted + fine-tuned had recall 1.0 with only 3.7 false alarms, but with 9 emergency texts in 3 families this is anecdote, not a result.
6. **Practical conclusions:** (a) keep the frozen e5 head as the offline yardstick; (b) the deployed layer must be rules/pathways with no weights, so the target to reach or beat on this LOFO is macro-F1 ~0.64-0.68 with emergency recall 100%; (c) more labelled CareCompass-style data (not more symptom data) is what would move the numbers; (d) the external dataset's lasting value is the 232-token multilingual symptom vocabulary (`dataset_vocab.json`), already in the intent gate.

**Limits:** 66 texts, 20 families, 9 emergency texts (3 families): intervals are wide (e.g. e5 frozen CI 0.44-0.75). Hyper-parameters were not searched. Adapted weights are in `pipeline/models_ft/` (not committed, not needed).

## 4. How much the weights were researched (honest account)

| Setting | Value | How it was set | Strength of evidence |
|---|---|---|---|
| Care-type C | 0.3 | best of 6 configs on the same LOFO folds | optimistic: chosen on the evaluation folds. All 6 beat the char baseline (F1 0.54-0.68), so the gain is real, the exact 0.68 is not |
| Emergency head C | 0.03 | tried after the multinomial head failed; picked for usable probability spread | weak (1-2 configs) |
| `tau_ask` 0.15 / `tau_emergency` 0.65 | from held-out LOFO scores | tau_ask = largest tau catching 9/9; tau_emergency = smallest with 0 false alarms | based on only 9 emergency texts in 3 families: wide intervals |
| Fine-tune: lr 3e-5, 12 epochs, batch 16, emergency class x3, class-balanced | fixed a priori | standard recipe + a rule that a missed emergency costs more than a false alarm | **not searched at all**: the GPU run will show whether it works |
| Stage A: lr 2e-5, 2 epochs, batch 32 | fixed a priori | standard recipe, no tuning on CareCompass folds | not searched |
| Fuse policy llm_first, trust 0.85, max follow-ups 2 | earlier design decision | not derived from data | none |

In short: only C and the two thresholds were looked at against data, and only on 66 texts. Everything else is a stated default. The GPU run exists to replace those defaults with measured values.

## 5. The GPU fine-tune script (`pipeline/scripts/gpu_finetune_multilingual.py`)

Run: `powershell -ExecutionPolicy Bypass -File pipeline\scripts\run_gpu_windows.ps1` (RTX 4060; torch CUDA 12.8; reads models from `..\models`, offline).
The runner does three things in order:
1. `prepare_multilingual_triage.py`: audits the CSV, extracts complaints, rebuilds `dataset_vocab.json`, writes report 09.
2. `gpu_encoder_eval.py`: baseline frozen and fine-tuned encoders on the 66 CareCompass texts (report 06b).
3. `gpu_finetune_multilingual.py` (per encoder: e5-base, MuRIL, XLM-R):
   - **Stage A** (external data): encoder + linear head learns to name the disease from the 1,976 complaints in 7 scripts (2 epochs, lr 2e-5). 10% of complaints (grouped by text) are held out and the disease accuracy is printed. Saved to `pipeline\models_ft\<name>-mlt`.
   - **Stage B** (CareCompass): leave-one-family-out for base-frozen, adapted-frozen, base-finetuned, adapted-finetuned (3 seeds for fine-tuned).
   - **Decision rule** written to `pipeline\reports\10_gpu_multilingual.md`: adopt the adapted encoder only if mean macro-F1 beats base AND emergency recall is not lower; otherwise keep the frozen e5 head.
Status: EXECUTED on 2026-10-25 (RTX 4060 Laptop); results in section 3b.
After a winner is chosen, exporting it to ONNX and re-fitting the heads is the next step (`export_router.py` with the new model dir).

## 6. Open work (next)
0. **WIRE the new modules into the graph** (see docs/NEXT_PHASE_PROMPT.md section 5). Then continue:
1. **Deterministic pathways (main goal):** write symptom pathways as data (JSON): entry cues (EN/Hinglish/Hindi) -> 2-4 questions -> disposition level + care type + explanation. Start with the Delhi-common set (fever, cough/breathing, diarrhoea/vomiting, chest pain, pregnancy, child fever, injury, diabetes/BP, elderly weakness). Content from public protocols; clinician review before use.
2. Rules vs learned model gap: use the e5 head offline as a yardstick (rules must reach its 0.68 macro-F1 on LOFO and keep 100% emergency recall).
3. Mood / distress layer (anxiety, panic, caregiver stress): deterministic cues + tone templates; the LLM does the wording.
4. Delhi data: localities -> PIN -> service area, emergency numbers, hospitals, seasonal flags.
5. Follow-up selection from DDXPlus evidence statistics, severity as auxiliary prior (approved), feeding the pathway question order.
6. Hindi/Hinglish names missing from all datasets: one-off LLM translation into a reviewable file (approved).
7. GPU runs are done (section 3b) and are not on the critical path any more. Only worth repeating if a much larger labelled CareCompass-style set appears.
8. Product: session storage and the "briefcase" of earlier documents (API is stateless today).
9. Known false alarm: "wound dressing and fever check at home" returns 112 (semantic safety net matches bleeding exemplars). Acceptable by policy, but a pathway layer should resolve it with one question.

## 7. How to run
- CPU re-train and export: `cd pipeline && python scripts/export_router.py --model-dir <models>/multilingual-e5-base`
- Dataset prep only: `python scripts/prepare_multilingual_triage.py --csv <datasets>/multilingual_triage/multilingual_medical_symptom_triage.csv`
- Tests: `cd backend && uv run pytest -q`
