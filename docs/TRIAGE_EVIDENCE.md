# Pain intake and uncertain danger answers

## Sources reviewed

- Supplied `STW_Manual_v1.pdf`: Indian Council of Medical Research / Department of Health Research,
  *Standard Treatment Workflows of India*, 2019, volume 1. PDF pages 13–15 cover stable angina,
  STEMI and unstable angina/NSTEMI. These distinguish pain location, timing, character and associated
  features. The unstable angina/NSTEMI workflow identifies ongoing/rest pain, breathlessness,
  sweating, syncope and instability as referral concerns. The manual addresses clinicians;
  its diagnostic procedures, treatment instructions and drug doses are not chatbot instructions.
- Supplied `CareCompass_CAI_Problem_Statement_Final.pdf`, all five pages, and repository
  `problem_statement.md`: ask 2–4 targeted questions, route to appropriate care, immediately
  escalate actual red flags, and support navigation without diagnosis or prescribing.
- [NHS chest pain guidance](https://www.nhs.uk/symptoms/chest-pain/) (checked 25 October 2026)
  also distinguishes persistent/sudden chest pain and associated warning signs from other presentations.
  The application retains its India emergency number and organiser red-flag contract.

## Implemented policy

1. Unspecified pain starts with an open location question in English, Hindi or Hinglish.
   Duration and associated symptoms follow, within the question budget. Do not suggest chest
   pain as an established location. Explicitly reported red flags still bypass questions.
2. Assistant questions are not patient evidence. The safety and triage model outputs cannot
   introduce chest pain without a chest-related cue in the current user episode.
3. `idk`, `pata nahi`, skipped and unrecognised answers remain unknown. They do not confirm
   danger signs. An otherwise unsupported model emergency on a purely uncertain reply
   does not create a confirmed red flag.
4. Unknown pathway danger answers, repeated unresolved safety questions and exhausted safety
   question budgets lead to same-day doctor assessment with conditional instructions to call
   112 for warning signs. Unknown danger answers never qualify for self-care. Confirmed
   emergency rules win even when another answer is unknown.
5. Panic changes tone and question priority; uncertainty during panic does not itself establish
   an emergency. The optional encoder does not escalate unlocated pain or a purely unknown
   reply on its score alone. Existing explicit red-flag rules remain the safety floor.

The uncertainty policy is an application design change, not a validated clinical threshold
or a claim that the manual endorses this chatbot. Pathway content remains marked UNREVIEWED.
Regression checks cover vague pain, location replies, multilingual unknown answers, model
overreach, question caps, panic and confirmed emergencies. No diagnosis or prescribing was added.

## Broader STW reference

The follow-up expansion indexes all 75 PDF pages and paraphrases the intake/referral portions of
all 53 clinical workflows across nine specialties. [The topic guide](STW_REFERENCE.md) contains
the reviewable summaries and synthetic decision examples. [The extraction manifest](STW_SOURCE_MANIFEST.json)
preserves source/page hashes, printed bibliography blocks and resource links, with incomplete links
kept separately. Printed resource links are source data, not verified current recommendations.

`backend/app/rules/stw_reference.json` supplies ten additional symptom groups and eleven focused
offline pathways. Intake captures explicit symptom status, age and measured values; condition intent
uses the same catalog; model prompts retrieve up to three relevant page-linked topics and related
examples. The original PDF and its treatment instructions are not inserted into model prompts.
Friendly introductions are visible in the follow-up card and included in voice replies.
