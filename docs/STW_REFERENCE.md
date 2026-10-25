# STW reference coverage

UNREVIEWED application adaptation; clinical content requires clinician review

Intake, intent, service navigation and referral cues only. No diagnosis, prescribing, treatment doses or invasive-procedure instructions.

Source: Standard Treatment Workflows of India, 2019 Edition, Volume I. Page numbers below are PDF page numbers, not printed page labels.

All 53 clinical workflows are indexed. Front matter, section dividers and contributor pages are not clinical topics.

## Runtime use

The same JSON supplies symptom aliases to intake/intent, focused offline pathways and bounded source context to the safety and triage prompts. A related topic is a reference, never a patient diagnosis. Explicit denials suppress topic cues; assistant questions cannot create patient facts.

## Topic index

| PDF page | Specialty | Workflow |
|---|---|---|
| 10 | cardiology | Atrial fibrillation |
| 11 | cardiology | Bradyarrhythmias |
| 12 | cardiology | Heart failure |
| 13 | cardiology | Stable angina |
| 14 | cardiology | ST elevation myocardial infarction |
| 15 | cardiology | Unstable angina / NSTEMI |
| 17 | ent | Acute rhinosinusitis |
| 18 | ent | Chronic rhinosinusitis |
| 19 | ent | Nosebleed |
| 20 | ent | Hearing impairment in children |
| 21 | ent | Neck space infection |
| 22 | ent | Otorrhoea |
| 23 | ent | Pharyngitis and sore throat |
| 25 | nephrology | Acute kidney injury |
| 26 | nephrology | Chronic kidney disease |
| 27 | nephrology | Glomerulonephritis |
| 28 | nephrology | Urinary tract infection |
| 30 | neurology | Acute paralysis |
| 31 | neurology | Dementia |
| 32 | neurology | Epilepsy |
| 33 | neurology | Headache |
| 34 | neurology | Neuroinfections |
| 35 | neurology | Stroke |
| 37 | obg | Antenatal management |
| 38 | obg | Dilatation and curettage |
| 39 | obg | Heavy menstrual bleeding |
| 40 | obg | Hysterectomy |
| 41 | obg | Postpartum haemorrhage |
| 42 | obg | Uterine fibroids and polyps |
| 44 | paediatrics | Acute encephalitis syndrome in children |
| 45 | paediatrics | Acute diarrhoea |
| 46 | paediatrics | Dengue fever |
| 47 | paediatrics | Fever in children |
| 48 | paediatrics | Sepsis and septic shock in children |
| 49 | paediatrics | Severe acute malnutrition with complications |
| 50 | paediatrics | Severe pneumonia in children |
| 52 | psychiatry | Alcohol use disorders |
| 53 | psychiatry | Anxiety disorders |
| 54 | psychiatry | Childhood behavioural disorders |
| 55 | psychiatry | Childhood emotional disorders |
| 56 | psychiatry | Children with developmental problems |
| 57 | psychiatry | Depression |
| 58 | psychiatry | Psychosis |
| 59 | psychiatry | Somatoform disorders |
| 61 | pulmonology | Acute respiratory infection in adults |
| 62 | pulmonology | Asthma |
| 63 | pulmonology | Chronic obstructive pulmonary disease |
| 64 | pulmonology | Respiratory failure |
| 66 | urology | Acute urinary retention in men |
| 67 | urology | Gross haematuria |
| 68 | urology | Male infertility |
| 69 | urology | Renal and ureteric stones |
| 70 | urology | Scrotal swelling |

## Atrial fibrillation (PDF page 10)

Ask about: Onset and duration of heartbeat change; Known heart condition; Fainting or current chest/breathing symptoms.

Referral concerns: Collapse; Ongoing chest pain; Breathing difficulty; Heavy bleeding while on blood thinners.

New symptoms need assessment today; a stable known condition can have a doctor follow-up.

## Bradyarrhythmias (PDF page 11)

Ask about: Measured pulse if available; Dizziness or fainting; Whether this is new or a planned review.

Referral concerns: Ongoing fainting; Chest pain; Reduced alertness.

Do not infer instability from a condition name; a clinician must interpret pulse and associated symptoms.

## Heart failure (PDF page 12)

Ask about: Change from usual breathing; New leg swelling; Reduced urine; Known diagnosis and current follow-up plan.

Referral concerns: Breathlessness at rest; Confusion; Collapse.

New worsening needs prompt in-person assessment; routine follow-up is different from an acute episode.

## Stable angina (PDF page 13)

Ask about: Location and character; Relation to exertion; Duration; Change from usual pattern.

Referral concerns: New or ongoing chest pain; Pain at rest; Sweating or breathlessness with chest pain.

Do not diagnose angina; current red-flag chest symptoms follow the emergency safety contract.

## ST elevation myocardial infarction (PDF page 14)

Ask about: Current episode versus past diagnosis; Chest discomfort location; Onset; Associated symptoms.

Referral concerns: Ongoing chest discomfort; Collapse; Breathing difficulty.

A suspected current attack needs emergency help; historical discharge/report review does not prove a current attack.

## Unstable angina / NSTEMI (PDF page 15)

Ask about: Pain at rest or exertion; New or worsening pattern; Sweating; Fainting.

Referral concerns: Ongoing or recurrent chest pain; Breathlessness; Syncope.

Navigation must not calculate a diagnosis or cardiac risk score from incomplete chat data.

## Acute rhinosinusitis (PDF page 17)

Ask about: Blocked nose or discharge; Facial symptoms; Duration; Eye symptoms.

Referral concerns: Eye swelling with visual change; Confusion; Severe deterioration.

Ask about the actual nose/face complaint; doctor assessment can determine whether ENT referral is needed.

## Chronic rhinosinusitis (PDF page 18)

Ask about: Duration and recurring pattern; Smell change; Allergy history; Previous ENT plan.

Referral concerns: New visual change; Eye swelling; Altered alertness.

Stable recurring symptoms suit doctor/ENT review; never prescribe antibiotics or decongestants.

## Nosebleed (PDF page 19)

Ask about: Is bleeding ongoing; Amount and duration; Injury; Blood thinner use if stated.

Referral concerns: Profuse or persistent bleeding; Fainting; Breathing problems.

Small stopped bleeding differs from heavy ongoing bleeding; avoid turning the word blood alone into a severity claim.

## Hearing impairment in children (PDF page 20)

Ask about: Child's age; Response to sound; Speech development; Sudden versus gradual change.

Referral concerns: Developmental regression; New marked hearing change; Other acute neurological symptoms.

Arrange hearing/ENT assessment; delayed speech alone is not a life-threatening emergency.

## Neck space infection (PDF page 21)

Ask about: Site and progression of swelling; Swallowing ability; Fever; Breathing.

Referral concerns: Breathing difficulty; Drooling or inability to swallow; Rapidly worsening neck swelling.

Potential airway compromise needs immediate help; uncomplicated throat discomfort needs different questions.

## Otorrhoea (PDF page 22)

Ask about: One or both ears; Pain or fever; Duration; Hearing change or injury.

Referral concerns: Severe headache with illness; Facial weakness; Severe deterioration.

Doctor/ENT examination is appropriate; do not suggest ear drops or ear instrumentation.

## Pharyngitis and sore throat (PDF page 23)

Ask about: Duration; Ability to drink and swallow; Fever; Voice change.

Referral concerns: Breathing difficulty; Unable to swallow saliva; Rapid neck swelling.

A simple sore throat is not automatically an emergency; assess swallowing and breathing before choosing care.

## Acute kidney injury (PDF page 25)

Ask about: Urine change; Recent vomiting or fluid loss; Swelling; Known kidney problem.

Referral concerns: Very low or absent urine; Breathing difficulty; Confusion.

New reduced urine needs medical assessment; never infer kidney failure solely from dark urine.

## Chronic kidney disease (PDF page 26)

Ask about: Routine follow-up versus new change; Urine; Swelling; Existing clinician plan.

Referral concerns: New breathlessness; Confusion; New major reduction in urine.

Review reports and follow-up needs; do not give blanket fluid, protein or medication advice to kidney patients.

## Glomerulonephritis (PDF page 27)

Ask about: Urine colour and amount; Face/leg swelling; Age; Known diagnosis.

Referral concerns: Seizure; Altered alertness; Breathing difficulty.

A doctor must assess urine changes and swelling; do not diagnose from a symptom pair.

## Urinary tract infection (PDF page 28)

Ask about: Burning or frequency; Fever or side pain; Pregnancy if stated; Ability to pass urine.

Referral concerns: Sudden inability to urinate; Severe illness; Confusion.

Symptoms need assessment rather than an automatic lab order or antibiotic recommendation.

## Acute paralysis (PDF page 30)

Ask about: Sudden versus longstanding weakness; Affected limbs; Time last well; Bladder/bowel change.

Referral concerns: Sudden weakness; Breathing or swallowing difficulty; New inability to walk.

New neurological loss needs urgent hospital evaluation; longstanding rehabilitation is a separate service need.

## Dementia (PDF page 31)

Ask about: Gradual memory change versus sudden confusion; Daily functioning; Caregiver concern; Recent illness or fall.

Referral concerns: Rapid deterioration; Seizure; New fever with confusion; Recent head injury.

Support patient and caregiver respectfully; do not label normal forgetfulness as dementia.

## Epilepsy (PDF page 32)

Ask about: Current event versus known history; Duration and recovery; First versus recurring event; Injury.

Referral concerns: Current/recent convulsion; Not recovering consciousness; Breathing difficulty.

Current red-flag seizures follow emergency rules; a stable history can need routine clinician follow-up.

## Headache (PDF page 33)

Ask about: Sudden versus gradual onset; New/worsening pattern; Severity; Associated neurological symptoms.

Referral concerns: Sudden extremely severe headache; Weakness or speech change; Fever with stiff neck; Reduced alertness.

Do not diagnose migraine or recommend medicines; screen warning signs then offer suitable assessment.

## Neuroinfections (PDF page 34)

Ask about: Fever; Alertness change; Seizures; Timing.

Referral concerns: Confusion or reduced responsiveness; Seizures; Breathing compromise.

Possible acute neurological infection needs urgent in-person care; historical diagnosis alone is not proof of current danger.

## Stroke (PDF page 35)

Ask about: Time last well; Sudden face/arm/speech change; Balance or vision change; New versus historical deficit.

Referral concerns: Sudden focal weakness; Slurred speech; New loss of balance or vision.

Do not delay emergency help for a current stroke pattern while collecting routine details.

## Antenatal management (PDF page 37)

Ask about: Pregnancy stage if known; Main concern; Existing maternity plan; Routine visit versus current symptoms.

Referral concerns: Heavy bleeding; Severe pain with faintness; Seizures; Breathing difficulty.

Routine antenatal review is a planned doctor/maternity service; symptoms require targeted assessment.

## Dilatation and curettage (PDF page 38)

Ask about: Planned procedure versus aftercare; Date if supplied; Current bleeding/pain; Clinician's aftercare plan.

Referral concerns: Severe pain; Heavy bleeding; Fever or marked deterioration after a procedure.

D&C requires a facility; home nursing can support only a stated aftercare task, not perform the procedure.

## Heavy menstrual bleeding (PDF page 39)

Ask about: Bleeding amount and duration; Faintness; Pregnancy possibility if relevant; Pattern change.

Referral concerns: Heavy ongoing loss with faintness; Collapse; Possible pregnancy with severe pain.

Distinguish a routine period concern from active major bleeding; arrange appropriate doctor review.

## Hysterectomy (PDF page 40)

Ask about: Planned surgery versus postoperative need; Wound/aftercare task; New symptoms.

Referral concerns: Heavy bleeding; Severe pain; Fever with deterioration.

Surgery belongs in a facility; a prescribed wound-care task can use home nursing.

## Postpartum haemorrhage (PDF page 41)

Ask about: Time since delivery; Is bleeding heavy now; Faintness; Alertness.

Referral concerns: Heavy bleeding after delivery; Collapse; Reduced alertness.

Current heavy postpartum bleeding needs emergency help; do not wait for a home caregiver.

## Uterine fibroids and polyps (PDF page 42)

Ask about: Known diagnosis versus new symptoms; Bleeding pattern; Pressure/pain; Report-review request.

Referral concerns: Heavy ongoing bleeding with weakness/faintness; Severe deterioration.

Doctor or gynaecology review; do not assume surgery is needed from a diagnosis label.

## Acute encephalitis syndrome in children (PDF page 44)

Ask about: Age; Fever; Alertness; Seizures; Recent exposures if already stated.

Referral concerns: Fever with reduced responsiveness; Seizures; Breathing difficulty.

Urgent assessment is guided by the child's reported condition, not a guessed diagnosis.

## Acute diarrhoea (PDF page 45)

Ask about: Age; Stool frequency and duration; Ability to drink; Urine output.

Referral concerns: Unable to drink; Repeated vomiting with reduced urine; Lethargy; Blood in stool.

Check hydration and age; avoid blanket advice to increase fluids in people with stated fluid restrictions.

## Dengue fever (PDF page 46)

Ask about: Duration of fever; Vomiting; Bleeding; Urine; Existing test or diagnosis.

Referral concerns: Persistent vomiting; Abdominal pain; Mucosal bleeding; Breathlessness; Altered consciousness.

Report warning symptoms without diagnosing dengue or interpreting platelet counts in isolation.

## Fever in children (PDF page 47)

Ask about: Exact age; Fever duration; Measured temperature if available; Feeding and responsiveness.

Referral concerns: Very young infant with fever; Poor feeding with serious illness; Reduced responsiveness; Breathing difficulty.

Do not assume every child is an infant; ask age when it changes the safe next step.

## Sepsis and septic shock in children (PDF page 48)

Ask about: Age; Feeding; Breathing; Alertness; Urine.

Referral concerns: Poor responsiveness; Convulsion; Cold/blue extremities with illness; Severe breathing difficulty.

A child with reported danger signs needs emergency care; a fever label alone does not establish sepsis.

## Severe acute malnutrition with complications (PDF page 49)

Ask about: Age; Feeding; Growth concern; Recent illness; Loss of acquired skills.

Referral concerns: Lethargy; Unable to feed; Severe dehydration; Seizures.

Nutrition/growth concerns need paediatric assessment; do not score malnutrition from chat alone.

## Severe pneumonia in children (PDF page 50)

Ask about: Age; Cough duration; Breathing effort; Feeding; Alertness.

Referral concerns: Unable to drink; Chest indrawing or severe breathing effort; Convulsions; Reduced responsiveness.

Assess actual breathing and feeding signs; diagnosis and treatment require a clinician.

## Alcohol use disorders (PDF page 52)

Ask about: Reason for seeking support; Last use if relevant; Withdrawal symptoms; Current safety.

Referral concerns: Seizures; Confusion; Immediate risk of harm.

Use nonjudgmental language; treatment/withdrawal planning needs a clinician, not unsupervised instructions to stop or change drugs.

## Anxiety disorders (PDF page 53)

Ask about: What feels most difficult; Duration; Sleep/function; Current safety.

Referral concerns: Current self-harm risk; New physical red flags.

Validate distress without promising everything is fine; anxiety does not prove or rule out a physical emergency.

## Childhood behavioural disorders (PDF page 54)

Ask about: Child's age; Specific change; Onset; Effect at home/school; Parent's main concern.

Referral concerns: Immediate danger to self or others; New neurological loss.

Ask respectfully without labelling the child; clinician assessment can guide referral and family support.

## Childhood emotional disorders (PDF page 55)

Ask about: Age; Change in mood; Stressors if volunteered; Daily functioning; Safety.

Referral concerns: Self-harm thoughts; Immediate threat or abuse-related danger.

Provide supportive clinician referral; avoid forcing sensitive details or assigning a diagnosis.

## Children with developmental problems (PDF page 56)

Ask about: Child's age; Which skill is delayed; Any loss of previously learned skills; Hearing concerns.

Referral concerns: Loss of acquired skills; Acute neurological symptoms.

Early paediatric/hearing assessment can help; delayed milestones alone are not an emergency.

## Depression (PDF page 57)

Ask about: Duration; Sleep/appetite; Daily functioning; Whether the person feels safe.

Referral concerns: Current self-harm thoughts or actions; Immediate danger.

Acknowledge distress and offer doctor/mental-health support; never diagnose from a short message.

## Psychosis (PDF page 58)

Ask about: New versus known symptoms; Current distress; Functioning; Safety and available support.

Referral concerns: Immediate risk of harm; Severe confusion; Unable to care for immediate needs.

Respond calmly without endorsing unusual beliefs; prompt clinician assessment is appropriate.

## Somatoform disorders (PDF page 59)

Ask about: What symptoms are troubling; Duration; Previous assessment if volunteered; Daily impact.

Referral concerns: New physical red flags; Current self-harm risk.

Treat the distress as real; do not dismiss symptoms as imaginary or assume a psychological cause.

## Acute respiratory infection in adults (PDF page 61)

Ask about: Cough duration; Fever; Breathing; Change from baseline; Known lung condition.

Referral concerns: Breathing difficulty; Confusion; Coughing significant blood.

Symptoms guide care navigation; do not diagnose pneumonia or prescribe antibiotics.

## Asthma (PDF page 62)

Ask about: Current breathing versus routine follow-up; Wheezing; Night symptoms; Existing action plan if stated.

Referral concerns: Unable to speak comfortably; Severe breathlessness; Drowsiness or blue lips.

Do not label a stable asthma history as a current attack or change inhaler doses.

## Chronic obstructive pulmonary disease (PDF page 63)

Ask about: Change from usual breathlessness; Sputum change; Known diagnosis; Current follow-up need.

Referral concerns: Sudden worsening at rest; Confusion; Blue lips; Drowsiness.

New deterioration needs assessment; do not use a generic oxygen target or treatment plan.

## Respiratory failure (PDF page 64)

Ask about: Breathing effort; Alertness; Measured reading only if available; Current versus past episode.

Referral concerns: Severe breathing effort; Blue lips; Altered alertness.

Life-threatening breathing symptoms need emergency help; never delay while asking for a device reading.

## Acute urinary retention in men (PDF page 66)

Ask about: Sudden inability versus longstanding poor flow; Last urine; Lower belly discomfort; Fever.

Referral concerns: Sudden inability to pass urine; Severe pain; Neurological loss.

Acute retention needs facility assessment; do not send a routine home catheter booking for an undiagnosed acute problem.

## Gross haematuria (PDF page 67)

Ask about: Visible blood versus colour change; Clots; Pain; Ability to pass urine; Duration.

Referral concerns: Clots with retention; Heavy ongoing bleeding; Faintness; Severe illness.

Visible blood needs assessment; do not infer cancer, infection or harmless food-related colour from chat.

## Male infertility (PDF page 68)

Ask about: Reason for consultation; Duration if volunteered; Prior assessment or report-review need.

Referral concerns: Sudden painful scrotal swelling is a separate acute symptom.

Offer a private doctor consultation and specialist referral where appropriate; no emergency from infertility alone.

## Renal and ureteric stones (PDF page 69)

Ask about: Location and duration of pain; Fever; Urine amount; Known stone history.

Referral concerns: No urine; Fever with chills; Persistent visible blood; Severe deterioration.

Do not diagnose a stone or recommend expulsive medication; new concerning symptoms require in-person assessment.

## Scrotal swelling (PDF page 70)

Ask about: Sudden versus gradual onset; Pain; Fever; Injury.

Referral concerns: Sudden severe testicular pain or swelling; Severe illness.

Acute painful swelling needs immediate facility assessment; a stable longstanding swelling needs doctor review.

## Synthetic decision examples

These are application examples, not quotations or labelled clinical training data.

- `dard hora hai` → `ask_location`. Generic symptom: do not assume chest pain.
- `peshab mein jalan ho rahi hai` → `stw_urinary`. Recognise urinary symptoms; ask ability to pass urine.
- `mere kaan se paani aa raha hai` → `stw_ear`. Recognise ear discharge; ask about hearing change.
- `gale mein kharash hai` → `stw_throat`. Assess swallowing rather than inventing chest symptoms.
- `pairon mein sujan hai` → `stw_swelling`. Recognise swelling; ask a relevant breathing question.
- `mann udaas hai aur neend nahi aa rahi` → `stw_mood`. Validate feelings and check current safety without diagnosing.
- `papa baar baar bhool rahe hain` → `stw_memory`. Distinguish sudden confusion from gradual memory change.
- `periods bahut zyada aa rahe hain` → `stw_periods`. Clarify bleeding severity and relevant maternity context.
- `baccha bolna nahi seekha` → `ask_child_age`. Development concern warrants assessment, not a guessed diagnosis.
- `dil tez dhadak raha hai` → `stw_palpitations`. Heartbeat change alone does not establish a heart attack.
- `papa ko CKD hai, reports doctor ko dikhani hain` → `teleconsultation`. Explicit report review takes precedence over symptom intake.
- `doctor ne catheter change bola hai, ghar pe nurse chahiye` → `home_nursing`. Planned nursing task, distinct from acute urinary retention.
- `ghar pe urine test ka sample dena hai` → `lab_test_home`. Explicit sample collection; do not diagnose UTI.
- `routine pregnancy checkup ke liye doctor se baat karni hai` → `teleconsultation`. Planned consultation is not an emergency.
- `I had a stroke last year and need a routine doctor follow-up` → `teleconsultation`. Historical diagnosis does not establish current stroke signs.
- `papa ko achanak seene mein dard hai aur saans nahi aa rahi` → `emergency_112`. Actual current red flags bypass further questions and matching.
- `idk` → `teleconsultation`. Unknown danger answer needs same-day assessment, not invented confirmation.
- `write a program about kidney stones` → `general`. Educational/software task is not a patient symptom episode.
