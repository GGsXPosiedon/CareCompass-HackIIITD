"""Build the curated STW navigation reference. No PDF text or prescribing instructions enter prompts.

Source: user-supplied ICMR/DHR Standard Treatment Workflows, 2019 volume I, 75 PDF pages.
Rows below paraphrase the intake/referral portions of all 53 clinical workflows. They are not diagnoses.
Run from any directory with Python's standard library; outputs are reproducible and reviewed in docs.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "backend/app/rules/stw_reference.json"

# page | specialty | id | title | condition aliases | useful intake | referral concerns | navigation scope
ROWS = """
10|cardiology|atrial_fibrillation|Atrial fibrillation|atrial fibrillation;afib;irregular heartbeat;dhadkan aniyamit;अनियमित धड़कन|Onset and duration of heartbeat change;Known heart condition;Fainting or current chest/breathing symptoms|Collapse;Ongoing chest pain;Breathing difficulty;Heavy bleeding while on blood thinners|New symptoms need assessment today; a stable known condition can have a doctor follow-up.
11|cardiology|bradyarrhythmia|Bradyarrhythmias|bradyarrhythmia;bradycardia;slow heartbeat;dhadkan dheemi;धीमी धड़कन|Measured pulse if available;Dizziness or fainting;Whether this is new or a planned review|Ongoing fainting;Chest pain;Reduced alertness|Do not infer instability from a condition name; a clinician must interpret pulse and associated symptoms.
12|cardiology|heart_failure|Heart failure|heart failure;congestive heart failure;dil ki pumping kam;हार्ट फेल्योर|Change from usual breathing;New leg swelling;Reduced urine;Known diagnosis and current follow-up plan|Breathlessness at rest;Confusion;Collapse|New worsening needs prompt in-person assessment; routine follow-up is different from an acute episode.
13|cardiology|stable_angina|Stable angina|stable angina;angina;एंजाइना|Location and character;Relation to exertion;Duration;Change from usual pattern|New or ongoing chest pain;Pain at rest;Sweating or breathlessness with chest pain|Do not diagnose angina; current red-flag chest symptoms follow the emergency safety contract.
14|cardiology|stemi|ST elevation myocardial infarction|stemi;myocardial infarction;हार्ट अटैक का फॉलोअप|Current episode versus past diagnosis;Chest discomfort location;Onset;Associated symptoms|Ongoing chest discomfort;Collapse;Breathing difficulty|A suspected current attack needs emergency help; historical discharge/report review does not prove a current attack.
15|cardiology|nstemi|Unstable angina / NSTEMI|nstemi;unstable angina;अस्थिर एंजाइना|Pain at rest or exertion;New or worsening pattern;Sweating;Fainting|Ongoing or recurrent chest pain;Breathlessness;Syncope|Navigation must not calculate a diagnosis or cardiac risk score from incomplete chat data.
17|ent|acute_sinusitis|Acute rhinosinusitis|acute sinusitis;rhinosinusitis;sinus infection;साइनस का संक्रमण|Blocked nose or discharge;Facial symptoms;Duration;Eye symptoms|Eye swelling with visual change;Confusion;Severe deterioration|Ask about the actual nose/face complaint; doctor assessment can determine whether ENT referral is needed.
18|ent|chronic_sinusitis|Chronic rhinosinusitis|chronic sinusitis;nasal polyps;purana sinus;पुराना साइनस|Duration and recurring pattern;Smell change;Allergy history;Previous ENT plan|New visual change;Eye swelling;Altered alertness|Stable recurring symptoms suit doctor/ENT review; never prescribe antibiotics or decongestants.
19|ent|epistaxis|Nosebleed|epistaxis;nosebleed;naak se khoon;नाक से खून|Is bleeding ongoing;Amount and duration;Injury;Blood thinner use if stated|Profuse or persistent bleeding;Fainting;Breathing problems|Small stopped bleeding differs from heavy ongoing bleeding; avoid turning the word blood alone into a severity claim.
20|ent|child_hearing|Hearing impairment in children|child hearing loss;hearing impairment;hearing problem;sunai kam;सुनाई कम|Child's age;Response to sound;Speech development;Sudden versus gradual change|Developmental regression;New marked hearing change;Other acute neurological symptoms|Arrange hearing/ENT assessment; delayed speech alone is not a life-threatening emergency.
21|ent|neck_infection|Neck space infection|neck space infection;neck abscess;gale mein sujan;गले में सूजन|Site and progression of swelling;Swallowing ability;Fever;Breathing|Breathing difficulty;Drooling or inability to swallow;Rapidly worsening neck swelling|Potential airway compromise needs immediate help; uncomplicated throat discomfort needs different questions.
22|ent|ear_discharge|Otorrhoea|otorrhoea;otorrhea;ear discharge;kaan se paani;कान से पानी|One or both ears;Pain or fever;Duration;Hearing change or injury|Severe headache with illness;Facial weakness;Severe deterioration|Doctor/ENT examination is appropriate; do not suggest ear drops or ear instrumentation.
23|ent|sore_throat|Pharyngitis and sore throat|pharyngitis;sore throat;gala kharab;gale mein kharash;गले में खराश|Duration;Ability to drink and swallow;Fever;Voice change|Breathing difficulty;Unable to swallow saliva;Rapid neck swelling|A simple sore throat is not automatically an emergency; assess swallowing and breathing before choosing care.
25|nephrology|aki|Acute kidney injury|acute kidney injury;aki;अचानक किडनी की परेशानी|Urine change;Recent vomiting or fluid loss;Swelling;Known kidney problem|Very low or absent urine;Breathing difficulty;Confusion|New reduced urine needs medical assessment; never infer kidney failure solely from dark urine.
26|nephrology|ckd|Chronic kidney disease|chronic kidney disease;ckd;kidney disease;gurde ki bimari;गुर्दे की बीमारी|Routine follow-up versus new change;Urine;Swelling;Existing clinician plan|New breathlessness;Confusion;New major reduction in urine|Review reports and follow-up needs; do not give blanket fluid, protein or medication advice to kidney patients.
27|nephrology|glomerulonephritis|Glomerulonephritis|glomerulonephritis;nephrotic syndrome;nephritic syndrome;नेफ्रोटिक सिंड्रोम|Urine colour and amount;Face/leg swelling;Age;Known diagnosis|Seizure;Altered alertness;Breathing difficulty|A doctor must assess urine changes and swelling; do not diagnose from a symptom pair.
28|nephrology|uti|Urinary tract infection|urinary tract infection;uti;urine infection;peshab mein infection;पेशाब में संक्रमण|Burning or frequency;Fever or side pain;Pregnancy if stated;Ability to pass urine|Sudden inability to urinate;Severe illness;Confusion|Symptoms need assessment rather than an automatic lab order or antibiotic recommendation.
30|neurology|acute_paralysis|Acute paralysis|acute paralysis;new paralysis;achanak lakwa;अचानक लकवा|Sudden versus longstanding weakness;Affected limbs;Time last well;Bladder/bowel change|Sudden weakness;Breathing or swallowing difficulty;New inability to walk|New neurological loss needs urgent hospital evaluation; longstanding rehabilitation is a separate service need.
31|neurology|dementia|Dementia|dementia;alzheimer;memory problem;yaaddasht kam;याददाश्त कम|Gradual memory change versus sudden confusion;Daily functioning;Caregiver concern;Recent illness or fall|Rapid deterioration;Seizure;New fever with confusion;Recent head injury|Support patient and caregiver respectfully; do not label normal forgetfulness as dementia.
32|neurology|epilepsy|Epilepsy|epilepsy;seizure disorder;mirgi;मिर्गी|Current event versus known history;Duration and recovery;First versus recurring event;Injury|Current/recent convulsion;Not recovering consciousness;Breathing difficulty|Current red-flag seizures follow emergency rules; a stable history can need routine clinician follow-up.
33|neurology|headache|Headache|headache;migraine;sir dard;sar dard;सिरदर्द|Sudden versus gradual onset;New/worsening pattern;Severity;Associated neurological symptoms|Sudden extremely severe headache;Weakness or speech change;Fever with stiff neck;Reduced alertness|Do not diagnose migraine or recommend medicines; screen warning signs then offer suitable assessment.
34|neurology|neuroinfection|Neuroinfections|neuroinfection;meningitis;encephalitis;brain infection;दिमाग का संक्रमण|Fever;Alertness change;Seizures;Timing|Confusion or reduced responsiveness;Seizures;Breathing compromise|Possible acute neurological infection needs urgent in-person care; historical diagnosis alone is not proof of current danger.
35|neurology|stroke|Stroke|stroke;cerebrovascular accident;लकवा|Time last well;Sudden face/arm/speech change;Balance or vision change;New versus historical deficit|Sudden focal weakness;Slurred speech;New loss of balance or vision|Do not delay emergency help for a current stroke pattern while collecting routine details.
37|obg|antenatal|Antenatal management|antenatal;prenatal;pregnancy checkup;garbhavati;गर्भवती|Pregnancy stage if known;Main concern;Existing maternity plan;Routine visit versus current symptoms|Heavy bleeding;Severe pain with faintness;Seizures;Breathing difficulty|Routine antenatal review is a planned doctor/maternity service; symptoms require targeted assessment.
38|obg|d_and_c|Dilatation and curettage|dilatation and curettage;dilation and curettage;d&c;डी एंड सी|Planned procedure versus aftercare;Date if supplied;Current bleeding/pain;Clinician's aftercare plan|Severe pain;Heavy bleeding;Fever or marked deterioration after a procedure|D&C requires a facility; home nursing can support only a stated aftercare task, not perform the procedure.
39|obg|menstrual_bleeding|Heavy menstrual bleeding|heavy menstrual bleeding;heavy periods;periods zyada;पीरियड में ज्यादा खून|Bleeding amount and duration;Faintness;Pregnancy possibility if relevant;Pattern change|Heavy ongoing loss with faintness;Collapse;Possible pregnancy with severe pain|Distinguish a routine period concern from active major bleeding; arrange appropriate doctor review.
40|obg|hysterectomy|Hysterectomy|hysterectomy;uterus removal;बच्चेदानी का ऑपरेशन|Planned surgery versus postoperative need;Wound/aftercare task;New symptoms|Heavy bleeding;Severe pain;Fever with deterioration|Surgery belongs in a facility; a prescribed wound-care task can use home nursing.
41|obg|postpartum_bleeding|Postpartum haemorrhage|postpartum haemorrhage;postpartum hemorrhage;delivery ke baad khoon;डिलीवरी के बाद खून|Time since delivery;Is bleeding heavy now;Faintness;Alertness|Heavy bleeding after delivery;Collapse;Reduced alertness|Current heavy postpartum bleeding needs emergency help; do not wait for a home caregiver.
42|obg|fibroids|Uterine fibroids and polyps|uterine fibroid;fibroids;uterine polyps;फाइब्रॉइड|Known diagnosis versus new symptoms;Bleeding pattern;Pressure/pain;Report-review request|Heavy ongoing bleeding with weakness/faintness;Severe deterioration|Doctor or gynaecology review; do not assume surgery is needed from a diagnosis label.
44|paediatrics|child_encephalitis|Acute encephalitis syndrome in children|acute encephalitis syndrome;child encephalitis;बच्चे का दिमागी बुखार|Age;Fever;Alertness;Seizures;Recent exposures if already stated|Fever with reduced responsiveness;Seizures;Breathing difficulty|Urgent assessment is guided by the child's reported condition, not a guessed diagnosis.
45|paediatrics|child_diarrhoea|Acute diarrhoea|acute diarrhoea;acute diarrhea;loose motions;dast;दस्त|Age;Stool frequency and duration;Ability to drink;Urine output|Unable to drink;Repeated vomiting with reduced urine;Lethargy;Blood in stool|Check hydration and age; avoid blanket advice to increase fluids in people with stated fluid restrictions.
46|paediatrics|dengue|Dengue fever|dengue;dengu;डेंगू|Duration of fever;Vomiting;Bleeding;Urine;Existing test or diagnosis|Persistent vomiting;Abdominal pain;Mucosal bleeding;Breathlessness;Altered consciousness|Report warning symptoms without diagnosing dengue or interpreting platelet counts in isolation.
47|paediatrics|child_fever|Fever in children|child fever;baby fever;bacche ko bukhar;बच्चे को बुखार|Exact age;Fever duration;Measured temperature if available;Feeding and responsiveness|Very young infant with fever;Poor feeding with serious illness;Reduced responsiveness;Breathing difficulty|Do not assume every child is an infant; ask age when it changes the safe next step.
48|paediatrics|child_sepsis|Sepsis and septic shock in children|child sepsis;septic shock;बच्चे में सेप्सिस|Age;Feeding;Breathing;Alertness;Urine|Poor responsiveness;Convulsion;Cold/blue extremities with illness;Severe breathing difficulty|A child with reported danger signs needs emergency care; a fever label alone does not establish sepsis.
49|paediatrics|malnutrition|Severe acute malnutrition with complications|malnutrition;poor weight gain;weight not increasing;wazan nahi badh raha;वजन नहीं बढ़ रहा|Age;Feeding;Growth concern;Recent illness;Loss of acquired skills|Lethargy;Unable to feed;Severe dehydration;Seizures|Nutrition/growth concerns need paediatric assessment; do not score malnutrition from chat alone.
50|paediatrics|child_pneumonia|Severe pneumonia in children|child pneumonia;bacche ko nimoniya;बच्चे को निमोनिया|Age;Cough duration;Breathing effort;Feeding;Alertness|Unable to drink;Chest indrawing or severe breathing effort;Convulsions;Reduced responsiveness|Assess actual breathing and feeding signs; diagnosis and treatment require a clinician.
52|psychiatry|alcohol_use|Alcohol use disorders|alcohol use disorder;alcohol dependence;sharab ki lat;शराब की लत|Reason for seeking support;Last use if relevant;Withdrawal symptoms;Current safety|Seizures;Confusion;Immediate risk of harm|Use nonjudgmental language; treatment/withdrawal planning needs a clinician, not unsupervised instructions to stop or change drugs.
53|psychiatry|anxiety|Anxiety disorders|anxiety;panic disorder;ghabrahat;चिंता;घबराहट|What feels most difficult;Duration;Sleep/function;Current safety|Current self-harm risk;New physical red flags|Validate distress without promising everything is fine; anxiety does not prove or rule out a physical emergency.
54|psychiatry|child_behaviour|Childhood behavioural disorders|child behavioural disorder;child behavioral disorder;adhd;बच्चे के व्यवहार की परेशानी|Child's age;Specific change;Onset;Effect at home/school;Parent's main concern|Immediate danger to self or others;New neurological loss|Ask respectfully without labelling the child; clinician assessment can guide referral and family support.
55|psychiatry|child_emotional|Childhood emotional disorders|childhood emotional disorder;school anxiety;school refusal;school nahi jana;स्कूल जाने से डर|Age;Change in mood;Stressors if volunteered;Daily functioning;Safety|Self-harm thoughts;Immediate threat or abuse-related danger|Provide supportive clinician referral; avoid forcing sensitive details or assigning a diagnosis.
56|psychiatry|development|Children with developmental problems|developmental delay;delayed speech;not speaking yet;bolna nahi seekha;बोलना नहीं सीखा|Child's age;Which skill is delayed;Any loss of previously learned skills;Hearing concerns|Loss of acquired skills;Acute neurological symptoms|Early paediatric/hearing assessment can help; delayed milestones alone are not an emergency.
57|psychiatry|depression|Depression|depression;low mood;mann udaas;man udaas;मन उदास|Duration;Sleep/appetite;Daily functioning;Whether the person feels safe|Current self-harm thoughts or actions;Immediate danger|Acknowledge distress and offer doctor/mental-health support; never diagnose from a short message.
58|psychiatry|psychosis|Psychosis|psychosis;schizophrenia;hearing voices;awaazein sunai;आवाजें सुनाई|New versus known symptoms;Current distress;Functioning;Safety and available support|Immediate risk of harm;Severe confusion;Unable to care for immediate needs|Respond calmly without endorsing unusual beliefs; prompt clinician assessment is appropriate.
59|psychiatry|somatic_distress|Somatoform disorders|somatoform;somatic symptom disorder;medically unexplained symptoms;बार बार तकलीफ|What symptoms are troubling;Duration;Previous assessment if volunteered;Daily impact|New physical red flags;Current self-harm risk|Treat the distress as real; do not dismiss symptoms as imaginary or assume a psychological cause.
61|pulmonology|adult_respiratory|Acute respiratory infection in adults|respiratory infection;chest infection;flu like illness;सांस का संक्रमण|Cough duration;Fever;Breathing;Change from baseline;Known lung condition|Breathing difficulty;Confusion;Coughing significant blood|Symptoms guide care navigation; do not diagnose pneumonia or prescribe antibiotics.
62|pulmonology|asthma|Asthma|asthma;asthama;dama;दमा;अस्थमा|Current breathing versus routine follow-up;Wheezing;Night symptoms;Existing action plan if stated|Unable to speak comfortably;Severe breathlessness;Drowsiness or blue lips|Do not label a stable asthma history as a current attack or change inhaler doses.
63|pulmonology|copd|Chronic obstructive pulmonary disease|copd;chronic obstructive pulmonary disease;पुरानी फेफड़े की बीमारी|Change from usual breathlessness;Sputum change;Known diagnosis;Current follow-up need|Sudden worsening at rest;Confusion;Blue lips;Drowsiness|New deterioration needs assessment; do not use a generic oxygen target or treatment plan.
64|pulmonology|respiratory_failure|Respiratory failure|respiratory failure;low oxygen;oxygen kam;ऑक्सीजन कम|Breathing effort;Alertness;Measured reading only if available;Current versus past episode|Severe breathing effort;Blue lips;Altered alertness|Life-threatening breathing symptoms need emergency help; never delay while asking for a device reading.
66|urology|retention|Acute urinary retention in men|urinary retention;unable to pass urine;peshab ruk gaya;पेशाब रुक गया|Sudden inability versus longstanding poor flow;Last urine;Lower belly discomfort;Fever|Sudden inability to pass urine;Severe pain;Neurological loss|Acute retention needs facility assessment; do not send a routine home catheter booking for an undiagnosed acute problem.
67|urology|haematuria|Gross haematuria|haematuria;hematuria;blood in urine;peshab mein khoon;पेशाब में खून|Visible blood versus colour change;Clots;Pain;Ability to pass urine;Duration|Clots with retention;Heavy ongoing bleeding;Faintness;Severe illness|Visible blood needs assessment; do not infer cancer, infection or harmless food-related colour from chat.
68|urology|male_infertility|Male infertility|male infertility;fertility concern;conceive nahi ho raha;संतान की परेशानी|Reason for consultation;Duration if volunteered;Prior assessment or report-review need|Sudden painful scrotal swelling is a separate acute symptom|Offer a private doctor consultation and specialist referral where appropriate; no emergency from infertility alone.
69|urology|stones|Renal and ureteric stones|renal stone;ureteric stone;kidney stone;pathri;पथरी|Location and duration of pain;Fever;Urine amount;Known stone history|No urine;Fever with chills;Persistent visible blood;Severe deterioration|Do not diagnose a stone or recommend expulsive medication; new concerning symptoms require in-person assessment.
70|urology|scrotal_swelling|Scrotal swelling|scrotal swelling;testicular swelling;testicle pain;andkosh mein sujan;अंडकोष में सूजन|Sudden versus gradual onset;Pain;Fever;Injury|Sudden severe testicular pain or swelling;Severe illness|Acute painful swelling needs immediate facility assessment; a stable longstanding swelling needs doctor review.
"""


def tr(en, hg, hi):
    return {"en": en, "hinglish": hg, "hi": hi}


TOPICS = []
for row in ROWS.strip().splitlines():
    page, specialty, key, title, aliases, intake, warnings, navigation = row.split("|")
    TOPICS.append(dict(id=key, specialty=specialty, pdf_page=int(page), title=title,
                       aliases=aliases.split(";"), intake=intake.split(";"), warning_signs=warnings.split(";"), navigation=navigation))

# These are observed symptom phrases, not condition diagnoses. Normalisation happens in the lexicon.
SYMPTOMS = {
    "urinary_symptoms": dict(pattern=r"burning (?:when|while) (?:passing urine|peeing)|burning urine|painful urination|urine (?:burning|problem)|peshab (?:me |mein )?(?:jalan|dard|dikkat|ruk)|baar baar peshab|पेशाब.*(?:जलन|दर्द|दिक्कत|रुक)|blood in urine|पेशाब में खून", label=tr("urinary trouble", "peshab ki pareshani", "पेशाब की परेशानी")),
    "ear_symptoms": dict(pattern=r"ear (?:ache|pain|discharge)|earache|hearing (?:loss|problem)|kaan (?:me |mein )?(?:dard|paani|taklif)|kaan se|sunai (?:kam|nahi)|कान.*(?:दर्द|पानी|बह)|सुनाई (?:कम|नहीं)", label=tr("ear or hearing trouble", "kaan ya sunai ki pareshani", "कान या सुनने की परेशानी")),
    "throat_symptoms": dict(pattern=r"sore throat|throat pain|gala (?:kharab|dukh)|gale (?:me |mein )?(?:dard|kharash|sujan)|गले.*(?:दर्द|खराश|सूजन)", label=tr("throat discomfort", "gale ki taklif", "गले की तकलीफ़")),
    "nasal_symptoms": dict(pattern=r"blocked nose|runny nose|nasal (?:block|congestion)|naak (?:band|beh)|नाक (?:बंद|बह)|sinus pain", label=tr("nose or sinus trouble", "naak ya sinus ki pareshani", "नाक या साइनस की परेशानी")),
    "swelling": dict(pattern=r"(?:feet|legs|face|ankle) (?:are )?(?:swollen|swelling)|swollen (?:feet|legs|face|ankle)|pair(?:on)? (?:me |mein )?sujan|chehre (?:me |mein |par )?sujan|(?:पैर|चेहरे).*सूजन", label=tr("swelling", "sujan", "सूजन")),
    "palpitations": dict(pattern=r"palpitation|heart (?:is )?racing|fast heartbeat|dhadkan (?:tez|badh)|dil (?:tez|jor se) dhadak|धड़कन (?:तेज|बढ़)", label=tr("heartbeat changes", "dhadkan mein badlav", "धड़कन में बदलाव")),
    "mood_symptoms": dict(pattern=r"low mood|feeling (?:low|anxious)|mann? (?:bahut )?udaas|ghabrahat|neend nahi|मन उदास|घबराहट|नींद नहीं", label=tr("mood or sleep concerns", "mann ya neend ki pareshani", "मन या नींद की परेशानी")),
    "memory_symptoms": dict(pattern=r"memory (?:loss|problem)|keeps forgetting|baar baar bhool|yaaddasht|याददाश्त|बार बार भूल", label=tr("memory changes", "yaaddasht mein badlav", "याददाश्त में बदलाव")),
    "menstrual_symptoms": dict(pattern=r"heavy periods|periods (?:bahut |zyada)|period (?:problem|late)|periods late|पीरियड.*(?:ज्यादा|परेशानी|देर)|माहवारी.*(?:दिक्कत|ज्यादा)", label=tr("period concerns", "period ki pareshani", "माहवारी की परेशानी")),
    "development_symptoms": dict(pattern=r"delayed speech|not speaking yet|developmental delay|bolna nahi seekha|wazan nahi badh|बोलना नहीं सीखा|वजन नहीं बढ़", label=tr("child development concerns", "bacche ki growth ya bolne ki pareshani", "बच्चे के विकास की परेशानी")),
}


def question(key, text, *, danger=False, options=None):
    return dict(id=key, text=text, danger=danger, options=options or [
        dict(id="yes", label=tr("Yes", "Haan", "हाँ")), dict(id="no", label=tr("No", "Nahi", "नहीं")),
        dict(id="unsure", label=tr("Not sure", "Pata nahi", "पता नहीं"))])


def pathway(key, title, cues, pages, danger, detail, reason, care="teleconsultation", emergency=True):
    # Same-day assessment is deliberate: these new pathways do not declare self-care from a short chat.
    return dict(id=key, title=title, cues=cues, source_pages=pages, source="ICMR_STW_2019_V1", reviewed=False,
                questions=[question("danger", danger, danger=True), question("detail", detail)],
                rules=[dict(when={"danger": ["yes"]}, disposition="emergency" if emergency else "urgent",
                            care_type="emergency_112" if emergency else care, urgency="emergency" if emergency else "same_day",
                            why=tr("You described a warning sign. Please get medical help now." if emergency else "This change needs a doctor to assess it today.",
                                   "Aapne khatre ka lakshan bataya hai. Abhi medical madad lein." if emergency else "Is badlav ka aaj doctor se assessment karwayein.",
                                   "आपने खतरे का लक्षण बताया है। अभी चिकित्सा सहायता लें।" if emergency else "इस बदलाव की आज डॉक्टर से जाँच करवाएँ।")),
                       dict(when={"detail": ["yes", "no", "unsure"]}, disposition="urgent", care_type=care, urgency="same_day", why=reason)])


PATHWAYS = [
    pathway("stw_headache", tr("Headache", "Sir dard", "सिरदर्द"), [r"\bheadache\b", r"\bmigraine\b", r"\b(?:sir|sar) (?:me |mein )?dard\b", "सिरदर्द", "सिर में दर्द"], [33, 35],
            tr("Did the headache start suddenly and become extremely painful within minutes?", "Kya sir dard achanak shuru hua aur kuch minute mein bahut tez ho gaya?", "क्या सिरदर्द अचानक शुरू होकर कुछ मिनट में बहुत तेज़ हो गया?"),
            tr("Is this headache new or getting worse than usual?", "Kya yeh sir dard naya hai ya pehle se badh raha hai?", "क्या यह सिरदर्द नया है या पहले से बढ़ रहा है?"),
            tr("Thanks for explaining. A doctor can assess the headache today and guide the next step.", "Batane ke liye shukriya. Aaj doctor sir dard ka assessment karke agla kadam bata sakte hain.", "बताने के लिए धन्यवाद। आज डॉक्टर सिरदर्द की जाँच करके अगला कदम बता सकते हैं।")),
    pathway("stw_urinary", tr("Urinary trouble", "Peshab ki pareshani", "पेशाब की परेशानी"), [SYMPTOMS["urinary_symptoms"]["pattern"], r"\burinary retention\b", r"\bhematuria\b", r"\bhaematuria\b"], [25, 28, 66, 67, 69],
            tr("Have you suddenly become unable to pass any urine?", "Kya achanak peshab bilkul band ho gaya hai?", "क्या अचानक पेशाब बिल्कुल बंद हो गया है?"),
            tr("Is there fever or pain in your side or back with the urinary trouble?", "Kya peshab ki pareshani ke saath bukhar ya peeth ke ek taraf dard hai?", "क्या पेशाब की परेशानी के साथ बुखार या पीठ के एक तरफ़ दर्द है?"),
            tr("A doctor should assess the urinary symptoms today and decide whether tests or an in-person examination are needed.", "Aaj doctor se peshab ki pareshani ka assessment karwayein. Woh batayenge ki jaanch ya saamne se check karna chahiye.", "आज डॉक्टर से पेशाब की परेशानी की जाँच करवाएँ। वे बताएँगे कि जाँच या सामने से परीक्षण की ज़रूरत है।")),
    pathway("stw_throat", tr("Throat or neck discomfort", "Gale ki taklif", "गले की तकलीफ़"), [SYMPTOMS["throat_symptoms"]["pattern"]], [21, 23],
            tr("Are you unable to swallow your own saliva?", "Kya apni laar bhi nigalne mein mushkil ho rahi hai?", "क्या अपनी लार भी निगल नहीं पा रहे हैं?"),
            tr("Is the throat or neck swelling getting worse?", "Kya gale ya gardan ki sujan badh rahi hai?", "क्या गले या गर्दन की सूजन बढ़ रही है?"),
            tr("A doctor can assess your throat today and advise if an ENT examination is needed.", "Aaj doctor gale ka assessment karke batayenge ki ENT se check karwana chahiye ya nahi.", "आज डॉक्टर गले की जाँच करके बताएँगे कि ENT परीक्षण की ज़रूरत है या नहीं।")),
    pathway("stw_ear", tr("Ear or hearing concern", "Kaan ki pareshani", "कान की परेशानी"), [SYMPTOMS["ear_symptoms"]["pattern"]], [20, 22],
            tr("Has the hearing suddenly become much worse?", "Kya achanak sunai bahut kam dene laga hai?", "क्या अचानक सुनाई बहुत कम देने लगा है?"),
            tr("Is there ear pain, discharge or fever?", "Kya kaan mein dard, paani aana ya bukhar hai?", "क्या कान में दर्द, पानी आना या बुखार है?"),
            tr("A doctor can assess the ear or hearing concern today and guide an ENT or hearing check.", "Aaj doctor kaan ya sunai ki pareshani ka assessment karke ENT ya hearing check ka agla kadam bata sakte hain.", "आज डॉक्टर कान या सुनने की परेशानी की जाँच करके ENT या श्रवण परीक्षण का अगला कदम बता सकते हैं।"), emergency=False),
    pathway("stw_nasal", tr("Nose or sinus concern", "Naak ki pareshani", "नाक की परेशानी"), [SYMPTOMS["nasal_symptoms"]["pattern"]], [17, 18],
            tr("Have the nose or facial symptoms come with a change in your vision?", "Kya naak ya chehre ki taklif ke saath dikhne mein badlav hua hai?", "क्या नाक या चेहरे की तकलीफ़ के साथ देखने में बदलाव हुआ है?"),
            tr("Have these symptoms been lasting or repeatedly coming back?", "Kya yeh taklif kaafi din se hai ya baar-baar laut rahi hai?", "क्या यह तकलीफ़ कई दिन से है या बार-बार लौट रही है?"),
            tr("A doctor can review the nose or sinus symptoms and guide the right care today.", "Aaj doctor naak ya sinus ki taklif samajhkar sahi care bata sakte hain.", "आज डॉक्टर नाक या साइनस की तकलीफ़ समझकर सही देखभाल बता सकते हैं।"), emergency=False),
    pathway("stw_swelling", tr("Swelling", "Sujan", "सूजन"), [SYMPTOMS["swelling"]["pattern"]], [12, 25, 26, 27],
            tr("Is the swelling happening along with difficulty breathing right now?", "Kya sujan ke saath abhi saans lene mein taklif bhi hai?", "क्या सूजन के साथ अभी साँस लेने में तकलीफ़ भी है?"),
            tr("Are you passing noticeably less urine than usual?", "Kya aam se kaafi kam peshab aa raha hai?", "क्या सामान्य से काफ़ी कम पेशाब आ रहा है?"),
            tr("A Medic can assess the swelling and check vitals today. A doctor can guide further tests if needed.", "Aaj Medic sujan aur vitals check kar sakte hain. Zaroorat ho to doctor aage ki jaanch bata sakte hain.", "आज मेडिक सूजन और शारीरिक माप जाँच सकते हैं। ज़रूरत होने पर डॉक्टर आगे की जाँच बता सकते हैं।"), care="paramedic_home_visit"),
    pathway("stw_palpitations", tr("Heartbeat changes", "Dhadkan mein badlav", "धड़कन में बदलाव"), [SYMPTOMS["palpitations"]["pattern"]], [10, 11],
            tr("Have you fainted with the heartbeat changes?", "Kya dhadkan mein badlav ke saath behoshi hui hai?", "क्या धड़कन में बदलाव के साथ बेहोशी हुई है?"),
            tr("Is this a new change or happening more often than usual?", "Kya yeh badlav naya hai ya pehle se zyada ho raha hai?", "क्या यह बदलाव नया है या पहले से ज़्यादा हो रहा है?"),
            tr("A doctor should review the heartbeat changes today and decide whether an in-person check is needed.", "Aaj doctor dhadkan ke badlav ka assessment karke batayenge ki saamne se check karna chahiye ya nahi.", "आज डॉक्टर धड़कन के बदलाव की जाँच करके बताएँगे कि सामने से परीक्षण की ज़रूरत है या नहीं।")),
    pathway("stw_mood", tr("Mood or sleep concern", "Mann ya neend ki pareshani", "मन या नींद की परेशानी"), [SYMPTOMS["mood_symptoms"]["pattern"]], [53, 55, 57, 59],
            tr("Are you at risk of hurting yourself right now?", "Kya abhi aapko khud ko nuksan pahunchane ka khatra lag raha hai?", "क्या अभी आपको खुद को नुकसान पहुँचाने का ख़तरा लग रहा है?"),
            tr("Is this making daily activities or sleep difficult?", "Kya isse roz ke kaam ya neend mein dikkat ho rahi hai?", "क्या इससे रोज़ के काम या नींद में दिक्कत हो रही है?"),
            tr("Thank you for sharing this. A doctor can listen and help you find suitable support today.", "Yeh batane ke liye shukriya. Aaj doctor aapki baat sunkar sahi support dhoondhne mein madad kar sakte hain.", "यह बताने के लिए धन्यवाद। आज डॉक्टर आपकी बात सुनकर सही सहायता ढूँढने में मदद कर सकते हैं।")),
    pathway("stw_memory", tr("Memory changes", "Yaaddasht mein badlav", "याददाश्त में बदलाव"), [SYMPTOMS["memory_symptoms"]["pattern"]], [31, 35],
            tr("Has the person suddenly become confused or hard to wake?", "Kya achanak uljhan hui hai ya unhe jagana mushkil ho raha hai?", "क्या अचानक उलझन हुई है या उन्हें जगाना मुश्किल हो रहा है?"),
            tr("Is the memory change affecting everyday activities?", "Kya yaaddasht ka badlav roz ke kaam par asar daal raha hai?", "क्या याददाश्त का बदलाव रोज़ के काम पर असर डाल रहा है?"),
            tr("A doctor can review the memory changes and help you and your family plan the next step.", "Doctor yaaddasht ke badlav ko samajhkar aap aur parivar ko agla kadam bata sakte hain.", "डॉक्टर याददाश्त के बदलाव को समझकर आपको और परिवार को अगला कदम बता सकते हैं।")),
    pathway("stw_periods", tr("Period concerns", "Period ki pareshani", "माहवारी की परेशानी"), [SYMPTOMS["menstrual_symptoms"]["pattern"]], [37, 39, 41, 42],
            tr("Is there heavy ongoing bleeding with faintness or feeling very unwell?", "Kya abhi bahut khoon beh raha hai aur behoshi jaisa ya bahut bura lag raha hai?", "क्या अभी बहुत खून बह रहा है और बेहोशी जैसा या बहुत बुरा लग रहा है?"),
            tr("Could you be pregnant, or have you recently given birth?", "Kya pregnancy ho sakti hai ya haal mein delivery hui hai?", "क्या गर्भावस्था की संभावना है या हाल में प्रसव हुआ है?"),
            tr("A doctor can assess the period concern today and guide appropriate women's health care.", "Aaj doctor period ki pareshani ka assessment karke sahi women's health care bata sakte hain.", "आज डॉक्टर माहवारी की परेशानी की जाँच करके सही महिला स्वास्थ्य देखभाल बता सकते हैं।")),
    pathway("stw_scrotal", tr("Scrotal pain or swelling", "Andkosh ki taklif", "अंडकोष की तकलीफ़"), [r"testic(?:le|ular) (?:pain|swelling)", r"scrotal (?:pain|swelling)", r"andkosh", "अंडकोष"], [70],
            tr("Did severe testicular pain or swelling start suddenly?", "Kya andkosh mein tez dard ya sujan achanak shuru hui?", "क्या अंडकोष में तेज़ दर्द या सूजन अचानक शुरू हुई?"),
            tr("Is there fever or a recent injury with it?", "Kya iske saath bukhar ya haal ki chot hai?", "क्या इसके साथ बुखार या हाल की चोट है?"),
            tr("A doctor should assess the pain or swelling today and guide an in-person examination.", "Aaj doctor dard ya sujan ka assessment karke saamne se check karne ka agla kadam bata sakte hain.", "आज डॉक्टर दर्द या सूजन की जाँच करके सामने से परीक्षण का अगला कदम बता सकते हैं।")),
]

EXAMPLES = [
    dict(input="dard hora hai", expect="ask_location", note="Generic symptom: do not assume chest pain."),
    dict(input="peshab mein jalan ho rahi hai", expect="stw_urinary", note="Recognise urinary symptoms; ask ability to pass urine."),
    dict(input="mere kaan se paani aa raha hai", expect="stw_ear", note="Recognise ear discharge; ask about hearing change."),
    dict(input="gale mein kharash hai", expect="stw_throat", note="Assess swallowing rather than inventing chest symptoms."),
    dict(input="pairon mein sujan hai", expect="stw_swelling", note="Recognise swelling; ask a relevant breathing question."),
    dict(input="mann udaas hai aur neend nahi aa rahi", expect="stw_mood", note="Validate feelings and check current safety without diagnosing."),
    dict(input="papa baar baar bhool rahe hain", expect="stw_memory", note="Distinguish sudden confusion from gradual memory change."),
    dict(input="periods bahut zyada aa rahe hain", expect="stw_periods", note="Clarify bleeding severity and relevant maternity context."),
    dict(input="baccha bolna nahi seekha", expect="ask_child_age", note="Development concern warrants assessment, not a guessed diagnosis."),
    dict(input="dil tez dhadak raha hai", expect="stw_palpitations", note="Heartbeat change alone does not establish a heart attack."),
    dict(input="papa ko CKD hai, reports doctor ko dikhani hain", expect="teleconsultation", note="Explicit report review takes precedence over symptom intake."),
    dict(input="doctor ne catheter change bola hai, ghar pe nurse chahiye", expect="home_nursing", note="Planned nursing task, distinct from acute urinary retention."),
    dict(input="ghar pe urine test ka sample dena hai", expect="lab_test_home", note="Explicit sample collection; do not diagnose UTI."),
    dict(input="routine pregnancy checkup ke liye doctor se baat karni hai", expect="teleconsultation", note="Planned consultation is not an emergency."),
    dict(input="I had a stroke last year and need a routine doctor follow-up", expect="teleconsultation", note="Historical diagnosis does not establish current stroke signs."),
    dict(input="papa ko achanak seene mein dard hai aur saans nahi aa rahi", expect="emergency_112", note="Actual current red flags bypass further questions and matching."),
    dict(input="idk", history=[dict(role="user", content="peshab mein jalan hai"), dict(role="assistant", content=PATHWAYS[1]["questions"][0]["text"]["hinglish"])], expect="teleconsultation", note="Unknown danger answer needs same-day assessment, not invented confirmation."),
    dict(input="write a program about kidney stones", expect="general", note="Educational/software task is not a patient symptom episode."),
]

DOC = dict(version="1.0.0", status="UNREVIEWED application adaptation; clinical content requires clinician review",
           source=dict(id="ICMR_STW_2019_V1", file="STW_Manual_v1.pdf", title="Standard Treatment Workflows of India, 2019 Edition, Volume I",
                       publisher="Indian Council of Medical Research / Department of Health Research, MoHFW, India", pdf_pages=75),
           scope="Intake, intent, service navigation and referral cues only. No diagnosis, prescribing, treatment doses or invasive-procedure instructions.",
           topics=TOPICS, symptom_concepts=SYMPTOMS, pathways=PATHWAYS, examples=EXAMPLES)


def main():
    OUT.write_text(json.dumps(DOC, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# STW reference coverage", "", DOC["status"], "", DOC["scope"], "",
             "Source: " + DOC["source"]["title"] + ". Page numbers below are PDF page numbers, not printed page labels.", "",
             "All 53 clinical workflows are indexed. Front matter, section dividers and contributor pages are not clinical topics.", "",
             "## Runtime use", "", "The same JSON supplies symptom aliases to intake/intent, focused offline pathways and bounded source context to the safety and triage prompts. A related topic is a reference, never a patient diagnosis. Explicit denials suppress topic cues; assistant questions cannot create patient facts.", "",
             "## Topic index", "", "| PDF page | Specialty | Workflow |", "|---|---|---|"]
    lines += [f"| {t['pdf_page']} | {t['specialty']} | {t['title']} |" for t in TOPICS]
    for t in TOPICS:
        lines += ["", f"## {t['title']} (PDF page {t['pdf_page']})", "", "Ask about: " + "; ".join(t["intake"]) + ".",
                  "", "Referral concerns: " + "; ".join(t["warning_signs"]) + ".", "", t["navigation"]]
    lines += ["", "## Synthetic decision examples", "", "These are application examples, not quotations or labelled clinical training data.", ""]
    lines += [f"- `{e['input']}` → `{e['expect']}`. {e['note']}" for e in EXAMPLES]
    doc = ROOT / "docs/STW_REFERENCE.md"
    doc.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Built {len(TOPICS)} topics, {len(SYMPTOMS)} symptom groups, {len(PATHWAYS)} pathways and {len(EXAMPLES)} examples.")


if __name__ == "__main__":
    main()
