"""Named-condition recognition for the intent layer (open vocabulary, deterministic, works with every LLM off).

Why this exists: a person who writes "mere aids h", "papa ko TB hai" or "मुझे कैंसर है" is describing a health need even
though no symptom word appears. The intent gate must never answer that with the generic "what is wrong?" redirect.

Layers (cheap -> broad), all offline:
  1. curated lexicon (English / Hinglish / Devanagari aliases, ~150 conditions, grouped by category)
  2. fuzzy matching of Latin tokens against single-word aliases (typos: "canser", "diabtes", "tuburculosis")
  3. medical morphology (-itis, -osis, -oma, -pathy, -aemia ...) for conditions the lexicon has never seen
  4. generic medical context words (bimari, chemo, dialysis, ICU, prescription, scan names, "tabiyat kharab" ...)

The module only RECOGNISES. It never picks a care type, never lowers an urgency and never diagnoses; it also never tells
the user what they "have". Emergencies are decided by safety.py before any of this is consulted.
"""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- lexicon -----------------------
# key -> (category, display name (en), [aliases]). Aliases are matched on lower-cased, NFKC text with word boundaries.
# Devanagari aliases are matched as written; Latin aliases also take part in fuzzy matching when they are one word >= 5 chars.
_RAW: dict[str, tuple[str, str, list[str]]] = {
    # --- infectious / long-term infections
    "hiv": ("infectious_chronic", "HIV/AIDS", ["aids", "hiv", "hiv positive", "hiv+", "एड्स", "एचआईवी", "एच आई वी", "art centre", "art center", "art medicine", "antiretroviral"]),
    "tb": ("infectious_chronic", "tuberculosis (TB)", ["tb", "t.b.", "tuberculosis", "tuberculous", "tubercolosis", "kshay", "kshay rog", "kshayrog", "टीबी", "टी बी", "क्षय रोग", "क्षयरोग", "तपेदिक", "dots", "dot centre"]),
    "hepatitis": ("infectious_chronic", "hepatitis", ["hepatitis", "hepatitis a", "hepatitis b", "hepatitis c", "hep b", "hep c", "hbv", "hcv", "jaundice", "piliya", "pilia", "peeliya", "पीलिया", "हेपेटाइटिस"]),
    "dengue": ("infectious_acute", "dengue", ["dengue", "dengu", "dengi", "डेंगू", "डेंगु", "platelets low", "platelet count", "platelets kam"]),
    "malaria": ("infectious_acute", "malaria", ["malaria", "malariya", "मलेरिया", "maleria"]),
    "typhoid": ("infectious_acute", "typhoid", ["typhoid", "tyfoid", "tifoid", "enteric fever", "मियादी बुखार", "टाइफाइड"]),
    "covid": ("infectious_acute", "COVID-19", ["covid", "covid19", "covid-19", "corona", "coronavirus", "कोविड", "कोरोना"]),
    "flu": ("infectious_acute", "flu", ["influenza", "swine flu", "h1n1", "bird flu", "viral fever", "viral infection", "flu"]),
    "chikungunya": ("infectious_acute", "chikungunya", ["chikungunya", "chikungunia", "chikangunya", "चिकनगुनिया"]),
    "chickenpox": ("infectious_acute", "chickenpox", ["chickenpox", "chicken pox", "chikenpox", "smallpox", "monkeypox", "mpox", "chhoti mata", "badi mata", "छोटी माता", "बड़ी माता", "चेचक"]),
    "measles": ("infectious_acute", "measles", ["measles", "khasra", "rubella", "खसरा"]),
    "mumps": ("infectious_acute", "mumps", ["mumps", "galsua", "गलसुआ"]),
    "cholera": ("infectious_acute", "cholera", ["cholera", "haija", "हैजा", "gastroenteritis", "food poisoning"]),
    "leprosy": ("infectious_chronic", "leprosy", ["leprosy", "kusht", "kusht rog", "kushth", "कुष्ठ", "कोढ़"]),
    "rabies": ("infectious_acute", "rabies / animal bite", ["rabies", "dog bite", "snake bite", "kutte ne kata", "kutta kata", "saanp ne kata", "saap ne kata", "monkey bite", "कुत्ते ने काटा", "सांप ने काटा", "tetanus"]),
    "pneumonia": ("respiratory", "pneumonia", ["pneumonia", "pnumonia", "nimoniya", "निमोनिया", "chest infection"]),
    "uti": ("infectious_acute", "urinary infection", ["uti", "urine infection", "urinary infection", "peshab me infection", "यूटीआई"]),
    "std": ("sexual_health", "sexually transmitted infection", ["std", "sti", "stds", "stis", "syphilis", "gonorrhea", "gonorrhoea", "chlamydia", "herpes", "genital warts", "hpv", "venereal", "gupt rog", "गुप्त रोग"]),
    "scabies": ("skin", "skin infection", ["scabies", "ringworm", "fungal infection", "eczema", "psoriasis", "vitiligo", "safed daag", "safed daag", "acne", "pimples", "hives", "urticaria", "dandruff", "khujli ki bimari", "daad", "दाद", "एक्ज़िमा", "सोरायसिस"]),
    "sepsis": ("infectious_acute", "serious infection", ["sepsis", "septicemia", "septicaemia", "blood infection", "abscess", "phoda", "फोड़ा", "gangrene", "cellulitis"]),
    "meningitis": ("infectious_acute", "meningitis", ["meningitis", "encephalitis", "japanese encephalitis", "polio"]),
    # --- cancer
    "cancer": ("cancer", "cancer", ["cancer", "cancers", "carcinoma", "tumor", "tumour", "tumors", "leukemia", "leukaemia", "lymphoma", "melanoma", "sarcoma", "malignant", "malignancy", "oncology", "oncologist", "chemo", "chemotherapy", "radiotherapy", "radiation therapy", "biopsy", "metastasis", "lump", "gaanth", "gantth", "ganth", "kainsar", "kainser", "कैंसर", "कैन्सर", "ट्यूमर", "गांठ", "गाँठ", "रसौली", "ब्लड कैंसर", "कीमो", "कीमोथेरेपी", "रेडियोथेरेपी"]),
    # --- chronic metabolic / endocrine / cardio
    "diabetes": ("chronic", "diabetes", ["diabetes", "diabetic", "diabetis", "sugar patient", "sugar ki bimari", "sugar high", "sugar low", "high sugar", "low sugar", "insulin", "madhumeh", "madhumeh", "मधुमेह", "डायबिटीज", "डायबटीज", "शुगर", "इंसुलिन", "hba1c"]),
    "hypertension": ("chronic", "high blood pressure", ["hypertension", "high bp", "low bp", "bp high", "bp low", "bp patient", "blood pressure", "uchch raktchap", "raktchap", "रक्तचाप", "हाई बीपी", "लो बीपी", "बीपी"]),
    "thyroid": ("chronic", "thyroid problem", ["thyroid", "hypothyroid", "hyperthyroid", "hypothyroidism", "hyperthyroidism", "goitre", "goiter", "थायरॉइड", "थाइरॉइड"]),
    "cholesterol": ("chronic", "cholesterol", ["cholesterol", "lipids", "triglycerides", "कोलेस्ट्रॉल"]),
    "obesity": ("chronic", "weight problem", ["obesity", "overweight", "weight gain", "weight loss", "motapa", "mota", "मोटापा", "underweight", "malnutrition", "kuposhan", "कुपोषण"]),
    "heart_disease": ("cardio", "heart condition", ["heart disease", "heart patient", "heart problem", "heart failure", "heart attack history", "bypass", "angioplasty", "stent", "pacemaker", "arrhythmia", "cardiac", "cardiologist", "angina", "dil ki bimari", "dil ka marij", "dil ki dikkat", "दिल की बीमारी", "हृदय रोग", "ह्रदय रोग", "हार्ट पेशेंट", "पेसमेकर"]),
    "stroke": ("neuro", "stroke / paralysis", ["stroke", "paralysis", "paralyzed", "paralysed", "paralytic", "hemiplegia", "paraplegia", "lakwa", "laqwa", "lakva", "falij", "फालिज", "लकवा", "अधरंग", "adharang"]),
    "anemia": ("blood", "anaemia / blood disorder", ["anemia", "anaemia", "low hemoglobin", "low haemoglobin", "hemoglobin low", "khoon ki kami", "खून की कमी", "sickle cell", "sickle cell anemia", "thalassemia", "thalassaemia", "thalesemia", "hemophilia", "haemophilia", "bleeding disorder", "blood clot", "clotting", "dvt", "thrombosis", "leucopenia", "platelet disorder", "थैलेसीमिया"]),
    # --- respiratory
    "asthma": ("respiratory", "asthma", ["asthma", "asthama", "asma", "asthma attack", "dama", "dumma", "दमा", "अस्थमा", "inhaler", "wheezing", "wheeze", "copd", "bronchitis", "emphysema", "bronchiectasis", "pulmonary fibrosis", "sleep apnea", "sleep apnoea", "ब्रोंकाइटिस"]),
    "sinus": ("respiratory", "sinus / allergy", ["sinus", "sinusitis", "allergy", "allergies", "hay fever", "rhinitis", "tonsil", "tonsils", "tonsillitis", "adenoids", "nasal polyp", "deviated septum", "साइनस", "एलर्जी"]),
    # --- renal / urinary / liver / gi
    "kidney": ("renal", "kidney problem", ["kidney failure", "kidney disease", "kidney problem", "kidney stone", "kidney stones", "renal failure", "renal", "ckd", "dialysis", "dialyses", "haemodialysis", "hemodialysis", "nephrologist", "nephritis", "kidney transplant", "gurda", "gurde", "gurdey", "pathri", "pathari", "pathri ka dard", "stone in kidney", "uric acid", "गुर्दा", "गुर्दे", "किडनी", "डायलिसिस", "पथरी", "यूरिक एसिड", "dialisis", "dailysis", "प्रोस्टेट", "prostate", "bph", "urinary retention", "incontinence", "catheter"]),
    "liver": ("gi", "liver problem", ["liver", "cirrhosis", "fatty liver", "liver failure", "liver damage", "liver disease", "liver transplant", "gallstone", "gallstones", "gall bladder", "gallbladder", "pancreatitis", "pancreas", "jigar", "jigar ki bimari", "लिवर", "जिगर", "पित्ताशय"]),
    "gi": ("gi", "digestive problem", ["ulcer", "peptic ulcer", "gastritis", "gerd", "acid reflux", "ibs", "irritable bowel", "crohn", "colitis", "appendicitis", "appendix", "piles", "haemorrhoids", "hemorrhoids", "bawasir", "bavasir", "fissure", "fistula", "hernia", "constipation", "kabz", "celiac", "coeliac", "lactose intolerance", "बवासीर", "अल्सर", "हर्निया", "गैस्ट्राइटिस", "अपेंडिक्स"]),
    # --- neuro / mental / geriatric
    "epilepsy": ("neuro", "epilepsy / seizures", ["epilepsy", "epileptic", "mirgi", "mirrgi", "mirgee", "daure", "daura", "daure padte", "seizure", "seizures", "convulsion", "convulsions", "fit aate", "मिर्गी", "दौरे", "दौरा", "अपस्मार"]),
    "dementia": ("neuro", "dementia / memory problem", ["dementia", "alzheimer", "alzheimers", "alzheimer's", "memory loss", "memory problem", "bhoolna", "bhulne ki bimari", "yaaddasht", "yaadasht", "याददाश्त", "भूलने की बीमारी", "अल्जाइमर", "डिमेंशिया"]),
    "parkinson": ("neuro", "Parkinson's disease", ["parkinson", "parkinsons", "parkinson's", "tremor", "tremors", "kampan", "कंपन", "पार्किंसन", "multiple sclerosis", "motor neuron", "muscular dystrophy", "cerebral palsy", "autism", "adhd", "down syndrome", "neuropathy", "neuralgia", "sciatica", "vertigo ki bimari", "ataxia", "myasthenia"]),
    "migraine": ("neuro", "migraine", ["migraine", "migrane", "migrain", "cluster headache", "आधासीसी", "माइग्रेन"]),
    "brain": ("neuro", "brain condition", ["brain tumor", "brain tumour", "brain hemorrhage", "brain haemorrhage", "hydrocephalus", "aneurysm", "head injury history", "brain surgery", "neurologist", "neurosurgeon", "दिमाग की बीमारी", "ब्रेन ट्यूमर"]),
    "depression": ("mental", "depression", ["depression", "depressed", "depresion", "udaas", "udasi", "udaasi", "mann nahi lagta", "mann nahi lag raha", "man nahi lagta", "dil bahut udaas", "डिप्रेशन", "उदासी", "burnout", "mental health", "mental stress", "mental pressure"]),
    "anxiety": ("mental", "anxiety", ["anxiety", "anxious", "panic attack", "panic attacks", "panic disorder", "ocd", "phobia", "social anxiety", "एंग्जायटी", ]),
    "psychiatric": ("mental", "mental health condition", ["bipolar", "bipolar disorder", "schizophrenia", "psychosis", "psychotic", "psychiatrist", "psychologist", "psychiatric", "mental illness", "mental patient", "paagalpan", "pagalpan", "ptsd", "eating disorder", "anorexia", "bulimia", "insomnia", "neend nahi aati", "neend ki bimari", "sleeplessness", "nashe ki lat", "addiction", "alcoholism", "alcohol addiction", "drug addiction", "nasha", "nasha mukti", "de-addiction", "deaddiction", "withdrawal", "smoking quit", "tobacco", "शराब की लत", "नशा", "नींद नहीं आती", "मानसिक रोग", "सिज़ोफ्रेनिया", "बाइपोलर"]),
    "self_harm": ("mental_urgent", "self-harm thoughts", ["suicidal", "suicide", "want to die", "wanna die", "end my life", "kill myself", "marna chahta", "marna chahti", "mar jaana chahta", "jeene ka mann nahi", "jina nahi chahta", "jina nahi chahti", "khudkushi", "आत्महत्या", "मरना चाहता", "मरना चाहती", "जीने का मन नहीं", "self harm", "self-harm", "cut myself"]),
    "elderly": ("geriatric", "elderly care need", ["bedridden", "bed ridden", "bed-ridden", "bedsore", "bed sore", "old age problem", "buzurg", "bujurg", "बुजुर्ग", "वृद्ध", "बिस्तर पर", "palliative", "hospice", "end of life", "last stage", "terminal", "terminally ill", "immobile", "frailty", "fall risk", "dementia care", "elderly care", "old age care"]),
    # --- maternal / women / child
    "pregnancy": ("maternal", "pregnancy-related", ["pregnant", "pregnancy", "pregnency", "preganancy", "garbh", "garbhavati", "garbhwati", "prasav", "delivery", "c-section", "csection", "cesarean", "caesarean", "antenatal", "prenatal", "postnatal", "postpartum", "miscarriage", "abortion", "ectopic", "morning sickness", "labour pain", "labor pain", "breastfeeding", "lactation", "gestational", "preeclampsia", "pre-eclampsia", "ivf", "infertility", "banjhpan", "pregnancy test", "गर्भवती", "गर्भ", "प्रेगनेंट", "प्रेग्नेंसी", "प्रेग्नेंट", "डिलीवरी", "गर्भपात", "प्रसव", "बांझपन"]),
    "gynae": ("maternal", "women's health condition", ["pcos", "pcod", "endometriosis", "fibroid", "fibroids", "menopause", "periods problem", "irregular periods", "heavy periods", "period problem", "leucorrhoea", "leucorrhea", "white discharge", "safed pani", "ovarian cyst", "cyst", "uterus", "hysterectomy", "vaginal infection", "yeast infection", "pelvic pain", "mastitis", "breast lump", "pap smear", "mammogram", "मासिक धर्म", "पीसीओएस", "पीरियड्स", "सफेद पानी", "माहवारी", "महावारी"]),
    "newborn": ("pediatric", "newborn / infant care", ["newborn", "new born", "infant", "neonatal", "nicu", "colic", "jaundice in baby", "baby jaundice", "vaccination", "vaccine", "vaccines", "immunization", "immunisation", "teeka", "tika", "टीका", "टीकाकरण", "growth problem", "bacche ki growth", "bachche ka weight", "teething", "diaper rash", "navjaat", "नवजात", "bed wetting", "bedwetting"]),
    # --- musculoskeletal / ortho / pain
    "arthritis": ("musculoskeletal", "arthritis / joint condition", ["arthritis", "arthritic", "rheumatoid", "rheumatism", "osteoarthritis", "gout", "gouty", "osteoporosis", "spondylitis", "spondylosis", "cervical", "lumbar", "slip disc", "slipped disc", "sciatica", "disc problem", "bone density", "jodo ka dard", "jodon ka dard", "gathiya", "gathia", "गठिया", "जोड़ों का दर्द", "आर्थराइटिस", "स्पॉन्डिलाइटिस", "ऑस्टियोपोरोसिस", "frozen shoulder", "tennis elbow", "carpal tunnel", "scoliosis", "flat foot", "knee replacement", "hip replacement", "joint replacement", "physio", "physiotherapy", "physiotherapist", "physiotherapy session", "fracture", "fractures", "plaster", "bone", "ligament", "acl", "tendon", "फ्रैक्चर", "हड्डी", "फिजियोथेरेपी"]),
    "surgery": ("procedure", "surgery / procedure aftercare", ["surgery", "operation", "operated", "post operative", "post-operative", "postoperative", "post surgery", "post-surgery", "stitches", "sutures", "transplant", "amputation", "colostomy", "ostomy", "tracheostomy", "ryles tube", "feeding tube", "peg tube", "icu", "hospital discharge", "discharged", "admitted", "operation ke baad", "surgery ke baad", "ऑपरेशन", "सर्जरी", "टांके", "भर्ती", "आईसीयू"]),
    # --- eye / ear / dental / skin
    "eye": ("eye_ent", "eye condition", ["cataract", "glaucoma", "retinopathy", "retina", "conjunctivitis", "pink eye", "eye flu", "myopia", "squint", "lazy eye", "night blindness", "blindness", "dry eyes", "stye", "motiyabind", "motiabind", "मोतियाबिंद", "आँख आना", "आंख आना", "ophthalmologist", "eye infection", "eye operation"]),
    "ent": ("eye_ent", "ear / nose / throat condition", ["hearing loss", "deafness", "tinnitus", "ear infection", "ear discharge", "kaan behna", "vertigo", "meniere", "sinus infection", "nosebleed history", "thyroid nodule", "voice loss", "hoarseness", "tonsil stone", "snoring", "बहरापन", "कान बहना"]),
    "dental": ("dental", "dental problem", ["dental", "dentist", "toothache", "tooth pain", "cavity", "root canal", "gum disease", "gum bleeding", "gingivitis", "wisdom tooth", "braces", "dant dard", "daant dard", "दांत दर्द", "दाँत", "मसूड़े"]),
    # --- rare / genetic / general
    "rare_genetic": ("rare", "rare or genetic condition", ["cystic fibrosis", "huntington", "marfan", "tay sachs", "gaucher", "phenylketonuria", "pku", "wilson disease", "spinal muscular atrophy", "duchenne", "genetic disorder", "genetic disease", "rare disease", "rare disorder", "rare genetic disorder", "hereditary", "congenital", "birth defect", "chromosomal", "syndrome", "lupus", "scleroderma", "sjogren", "vasculitis", "sarcoidosis", "autoimmune", "autoimmune disease", "immune disorder", "addison", "cushing", "acromegaly", "hemochromatosis", "amyloidosis", "porphyria", "myeloma", "aplastic anemia", "aplastic anaemia"]),
    "general_illness": ("general", "illness", ["bimari", "bimaari", "beemari", "bimar", "bimaar", "bemari", "बीमारी", "बिमारी", "बीमार", "rog", "rogi", "marij", "मरीज", "मरीज़", "रोग", "रोगी", "patient", "illness", "disease", "diseases", "disorder", "infection", "infections", "virus", "viral", "condition", "chronic", "chronic illness", "chronic disease", "terminal illness", "long illness", "lambi bimari", "purani bimari", "old illness", "medical condition", "health issue", "health problem", "health condition", "medical history", "medical problem", "health scare", "diagnosed", "diagnosis", "tested positive", "test positive", "positive aaya", "positive aya", "positive report", "report positive", "report aayi", "report aaya", "report me aaya", "pata chala", "pata chala hai", "detected", "relapse", "recurrence", "flare up", "flare-up", "sehat", "sehat kharab", "swasthya", "tabiyat", "tabiyat kharab", "tabiat", "tabiyat theek nahi", "tabyat", "तबीयत", "तबियत", "सेहत", "स्वास्थ्य", "haalat kharab", "halat kharab", "हालत खराब", "kuch ho gaya", "kuch hogaya", "kuch hua", "kuch ho gya", "kuch ho gaya hai", "कुछ हो गया", "कुछ हुआ", "feeling low", "not feeling well", "feel unwell", "feeling unwell", "feel sick", "feeling sick", "feeling off", "under the weather", "not well", "ill", "sickly", "ailing", "ailment", "ailments", "sick leave", "medically unfit", "unfit"]),
}

# Common misspellings / romanisations of SHORT names. Fuzzy matching only runs on long words (too many look-alikes among short
# ones: stent/spent, liver/lives, gurde/guide), so the typos people really make for short names are listed outright.
_TYPOS = {
    "cancer": ["canser", "cansar", "cancor", "kanser", "kansar", "cancr", "cancar", "kainsar", "caancer", "cancers"],
    "hiv": ["hiv+ve", "h.i.v", "aids hai", "aidz", "ads patient"],
    "tb": ["tibi", "t b", "tubercolosis", "tuberclosis", "tuburculosis", "tuberculosys"],
    "diabetes": ["diabtes", "diabetis", "diabeties", "diabeetes", "diabates", "diabitis", "diabetic", "sugar ki bimari", "shugar"],
    "dengue": ["dengu", "dengy", "dengi", "dengee", "denge fever", "denguee"],
    "malaria": ["maleria", "malarya", "malariya", "malaaria"],
    "typhoid": ["tyfoid", "tifoid", "typhoyd", "typoid", "taiphoid"],
    "hepatitis": ["hepatits", "hepatities", "hepatiis", "hepatitus", "jaundis", "jandice", "jondice"],
    "asthma": ["asthama", "asma", "astma", "asthmaa", "athsma", "ashtma"],
    "epilepsy": ["epilepcy", "epelepsy", "epilepsi", "mirgee", "mirrgi", "mergi", "mirgi ka daura"],
    "stroke": ["strok", "stoke attack", "brain stroke", "paralisis", "paralyses"],
    "kidney": ["kidny", "kidnee", "kidni", "kidney fail", "gurdey ki bimari", "dialisis", "dailisis"],
    "anemia": ["anaemia", "anamia", "aneamia", "anemic", "anaemic"],
    "depression": ["depresion", "depressoin", "dipression", "depress"],
    "pregnancy": ["pregnency", "pregnent", "pragnent", "pregnat", "pregnet", "pregant", "prgnant", "pregancy"],
    "thyroid": ["thyrod", "thiroid", "thyriod", "thyroyd"],
    "arthritis": ["arthrities", "artheritis", "arthiritis", "arthritus"],
}
for _k, _extra in _TYPOS.items():
    _RAW[_k][2].extend(_extra)

# Medication / care words: not conditions, but they prove the message is a health message.
_CARE_WORDS = [
    "medicine", "medicines", "medication", "medications", "tablet", "tablets", "capsule", "syrup", "dawai", "dawa", "dawaai", "goli", "golis", "injection", "inject",
    "dose", "prescription", "pharmacy", "chemist", "medical store", "medicine store", "hospital", "hospitals", "aspatal", "asptal", "clinic", "dispensary", "nursing home",
    "doctor", "dr", "dr.", "daktar", "doktor", "vaidya", "hakim", "specialist", "physician", "surgeon", "oncologist", "cardiologist", "neurologist", "nephrologist", "gynaecologist", "gynecologist", "pediatrician", "paediatrician", "dermatologist", "orthopedic", "orthopaedic", "urologist", "psychiatrist", "ent", "gp",
    "nurse", "nursing", "caregiver", "attendant", "ward boy", "ayah", "compounder",
    "ambulance", "oxygen", "oxygen cylinder", "ventilator", "bipap", "cpap", "nebuliser", "nebulizer", "glucometer", "bp machine", "pulse oximeter", "spo2", "wheelchair", "walker", "hospital bed",
    "x-ray", "xray", "x ray", "mri", "ct scan", "ultrasound", "sonography", "usg", "ecg", "ekg", "echo", "2d echo", "angiography", "endoscopy", "colonoscopy", "mammography", "pet scan", "blood report", "lab report", "medical report", "test report", "reports",
    "blood test", "urine test", "lab test", "pathology", "checkup", "check-up", "check up", "health check", "full body checkup", "second opinion",
    "therapy", "therapist", "counselling", "counseling", "counsellor", "counselor", "rehab", "rehabilitation", "treatment", "treatments", "ilaj", "ilaaj", "upchar", "इलाज", "उपचार", "दवा", "दवाई", "गोली", "डॉक्टर", "अस्पताल", "नर्स", "टेस्ट", "जांच", "जाँच", "रिपोर्ट", "एम्बुलेंस", "एंबुलेंस",
    "symptom", "symptoms", "lakshan", "लक्षण", "side effect", "side effects", "reaction", "overdose", "withdrawal",
    "pregnant", "blood group", "donor", "blood donation", "organ donation",
    "health", "healthcare", "medical", "medically", "sehatmand", "healthy", "diet plan", "diet chart", "nutritionist", "dietician", "dietitian",
]

# --------------------------------------------------------------------------- compiled matchers ------------------
_WORD_L = r"(?<![\wऀ-ॿ])"
_WORD_R = r"(?![\wऀ-ॿ])"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", t).lower()
    t = re.sub(r"[​-‍﻿]", "", t)
    return t


def _alias_rx(aliases: list[str]) -> re.Pattern:
    parts = []
    for a in sorted({_norm(x) for x in aliases}, key=len, reverse=True):
        esc = re.escape(a).replace(r"\ ", r"[\s\-]+")
        parts.append(esc)
    return re.compile(_WORD_L + "(?:" + "|".join(parts) + ")" + _WORD_R)


@dataclass(frozen=True)
class ConditionMatch:
    key: str
    category: str
    name: str
    matched: str
    how: str  # lexicon | fuzzy | morphology | context

    def __str__(self) -> str:  # pragma: no cover - debugging helper
        return f"{self.key}<{self.matched}>[{self.how}]"


from .clinical_reference import load as load_reference

for _topic in load_reference()["topics"]:
    _RAW["stw_" + _topic["id"]] = (_topic["specialty"], _topic["title"], _topic["aliases"])

_CONDITIONS = {k: (cat, name, _alias_rx(al)) for k, (cat, name, al) in _RAW.items()}
_CARE_RX = _alias_rx(_CARE_WORDS)

# words that the "general illness" bucket contains but that would be too weak alone (e.g. "ill" inside chit-chat is fine,
# "condition"/"patient"/"virus"/"unfit" as a bare word are weak). They count as a *context* signal, not a named condition.
_WEAK_GENERAL = {"condition", "patient", "virus", "viral", "infection", "infections", "disorder", "disease", "diseases", "chronic",
                 "medical condition", "unfit", "detected", "diagnosed", "diagnosis", "relapse", "recurrence", "ill", "sehat", "swasthya"}

# Latin tokens for fuzzy matching: single-word aliases >= 5 letters, grouped by first letter (typo on 1st letter is rare)
_FUZZY_INDEX: dict[str, list[tuple[str, str]]] = {}
for _k, (_cat, _n, _al) in _RAW.items():
    if _k == "general_illness":
        continue
    for _a in _al:
        a = _norm(_a)
        if re.fullmatch(r"[a-z]{7,}", a):
            _FUZZY_INDEX.setdefault(a[0], []).append((a, _k))

# English / Hinglish words one edit away from a condition name that must never be read as that condition
_FUZZY_BLOCK = {
    "cancel", "cancels", "cancer's", "stroke's", "strike", "strikes", "stoke", "stoked", "brake", "bronze", "diabetes's",
    "dental's", "mental", "metal", "medal", "medals", "medical's", "madam", "damage", "dame", "dumb", "ulcer's", "ulster",
    "panel", "panic's", "cold", "colds", "cough's", "flow", "flew", "flaw", "fleet", "float", "flute", "lumps", "lamp", "limp",
    "hernia's", "polio's", "theory", "thorough", "through", "thyroid's", "tumble", "tumbler", "humor", "rumor", "tutor", "nurse's",
    "cystic's", "liver's", "lover", "lived", "liner", "livery", "diver", "driver", "rivers", "tbh", "tablet's", "surgery's",
    "heard", "heart's", "hearts", "earth", "hearth", "bones", "bone's", "phone", "bonus", "lakes", "lakh", "lakhs", "dawat",
    "report's", "reports", "reporter", "porter", "shelter", "kidnap", "kidding", "kitten", "mumbai", "pilot", "pills", "piles'",
    "gouts", "gone", "gain", "gaint", "giant", "wheel", "wheels", "whale", "while", "white", "whole", "wheat", "sugar's",
    "stress's", "stresses", "strength", "dossier", "doctor's", "dock", "dosa", "dose's", "doses", "dosage", "cyst's",
    "habit", "rabbit", "rabid", "ribbon", "ration", "rations", "ratio", "raise", "rains", "remit", "relax", "relief", "relay",
    "teeka", "teeth", "teach", "tiger", "tiki", "taste", "tests", "tasty", "lupin", "lunch", "lungs", "loops", "loupe",
    "migrate", "migrant", "migration", "micro", "midget", "might", "milk", "mills", "mines", "miner",
    "swiss", "twist", "sweet", "sweat", "swell", "swelling", "swollen", "sweater",
    "allergy's", "energy", "energies", "enemy", "angry", "anger", "angel", "angle", "anger's",
    "stone", "stones", "store", "stored", "storm", "story", "stove", "straw", "stray", "stream", "street",
    "burst", "burns", "burnt", "burner", "bursts", "bureau", "bureaucrat",
    "flights", "fights", "fight", "light", "lights", "night", "nights", "sight", "tight",
    "brain's", "braid", "brains", "brand", "brave", "bread", "break", "breed", "brief", "bring",
    "aspect", "asset", "assist", "asthma's", "arthur", "arthritis's", "papa", "pappu",
    "sinus's", "sinks", "since", "singer", "single", "sinew", "sinner", "sins",
    "ulcers", "uncle", "under", "union", "unite", "units", "until",
    "scoring", "operational", "operations", "confusion", "discarded", "teaching", "teacher", "teachers", "reaching", "beaching", "weekly", "weekend", "weight", "weigh", "weird", "welcome", "well", "wells",
}


def _lev_le(a: str, b: str, limit: int) -> bool:
    """True if edit distance(a, b) <= limit (limit is 1 or 2). Small and dependency free."""
    if abs(len(a) - len(b)) > limit:
        return False
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        best = cur[0]
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb))
            best = min(best, cur[j])
        if best > limit:
            return False
        prev = cur
    return prev[-1] <= limit


_EXACT_TOKENS = {_norm(a) for _k, (_c, _nm, _al) in _RAW.items() for a in _al}


def _fuzzy(tokens: list[str]) -> ConditionMatch | None:
    for tok in tokens:
        if tok in _EXACT_TOKENS:
            continue  # a known word (possibly negated or context-blocked) is never "a typo of" another condition
        if len(tok) < 7 or not re.fullmatch(r"[a-z]+", tok) or tok in _FUZZY_BLOCK:
            continue
        limit = 1 if len(tok) <= 9 else 2
        for alias, key in _FUZZY_INDEX.get(tok[0], []):
            if alias == tok:
                continue  # exact hits are the lexicon layer's job (and may be negated/blocked elsewhere)
            if limit == 2 and len(tok) < 11 and tok[-2:] != alias[-2:]:
                continue  # two edits on a short word must at least keep the ending
            if abs(len(alias) - len(tok)) <= limit and len(alias) >= 5 and _lev_le(tok, alias, limit):
                if alias in _FUZZY_BLOCK:
                    continue
                cat, name, _ = _CONDITIONS[key]
                return ConditionMatch(key, cat, name, tok, "fuzzy")
    return None


# Medical-looking suffixes: catches conditions that were never listed ("gastroparesis", "vasculitis", "neuroblastoma").
_MORPH = re.compile(r"^[a-z]{3,}(?:itis|osis|oma|omas|pathy|opathy|aemia|emia|algia|plegia|ectomy|plasty|oscopy|ostomy|trophy|penia|cytosis|uria|rrhea|rrhoea|megaly|sclerosis|paresis|dystonia|dysplasia|lithiasis)$")
_MORPH_BLOCK = {"emotion", "promotion", "commotion", "lotion", "motion", "notion", "potion", "devotion", "pathology_", "diploma", "sitcom", "aroma", "coma_", "agama", "comma", "panorama",
                "melodrama", "drama", "dilemma", "sherlock", "genoma", "kosovo", "enigma", "stigma", "stigmas", "llama", "pyjama", "pajama", "bikini", "sympathy", "empathy", "apathy", "telepathy", "antipathy",
                "osteopathy_", "homeopathy", "naturopathy", "allopathy", "ayurveda", "sociopathy", "psychopathy", "ghost", "most", "post", "host", "dosa", "emphasis", "analysis", "basis", "oasis", "thesis", "hypothesis",
                "synthesis", "diagnosis", "prognosis", "genesis", "kinesis", "paralysis", "metamorphosis", "mitosis_", "emoji", "bonsai", "sumo", "vitamin", "ceramic"}
_MORPH_TOKEN = re.compile(r"[a-z]+")


def _morphology(tokens: list[str]) -> ConditionMatch | None:
    for tok in tokens:
        if len(tok) >= 7 and tok not in _MORPH_BLOCK and _MORPH.match(tok):
            return ConditionMatch("unlisted_condition", "other", "a medical condition", tok, "morphology")
    return None


# --------------------------------------------------------------------------- public api ---------------------
_NEG_BEFORE = re.compile(r"(?:\b(?:no|not|without|never|neither|nor|zero|negative for|ruled out|rule out)\s+(?:\S+\s+){0,1}|\bbina\s+|\bkoi\s+)$")
_NEG_AFTER = re.compile(r"^\s*(?:(?:ka|ki|ke)\s+)?(?:(?:hai|h|tha|thi|hain|hua|hui|ho)\s+)?(?:nahi|nhi|nahin|nai|no|not|negative|nahi hai|नहीं|नही)\b")


def _negated(t: str, start: int, end: int) -> bool:
    """'I do not have cancer', 'cancer nahi hai', 'no TB': a negated mention is not a named condition."""
    before = t[max(0, start - 28):start]
    after = t[end:end + 24]
    if re.search(r"\b(?:dont|don't|do not|doesnt|doesn't|does not|didnt|didn't|did not|havent|haven't|hasnt|hasn't)\s+(?:have|has|had)\s+(?:a |an |any |the )?$", before):
        return True
    return bool(_NEG_BEFORE.search(before) or _NEG_AFTER.search(after))


_AID_CONTEXT = re.compile(r"\b(?:hearing|teaching|visual|learning|mobility|study|audio|walking|first|financial|legal|digital|sales|memory|aid)\s+aids?\b|\bfirst aid\b")


def find_conditions(text: str, limit: int = 4) -> list[ConditionMatch]:
    """Every named condition in the message (strongest layer first, de-duplicated by key)."""
    t = _norm(text)
    if not t.strip():
        return []
    out: list[ConditionMatch] = []
    seen: set[str] = set()
    for key, (cat, name, rx) in _CONDITIONS.items():
        m = next((x for x in rx.finditer(t) if not _negated(t, x.start(), x.end())), None)
        if not m:
            continue
        hit = m.group(0).strip()
        if key == "general_illness" and hit in _WEAK_GENERAL:
            continue
        if hit in ("aids", "aid") and _AID_CONTEXT.search(t[max(0, m.start() - 20):m.end()]):
            continue
        if key not in seen:
            seen.add(key)
            out.append(ConditionMatch(key, cat, name, hit, "lexicon"))
    tokens = re.findall(r"[a-z]+", t)
    if not out:
        for fn in (_fuzzy, _morphology):
            m = fn(tokens)
            if m:
                out.append(m)
                break
    # a specific condition outranks the catch-all 'general illness' bucket
    out.sort(key=lambda m: (m.key == "general_illness", m.how != "lexicon"))
    return out[:limit]


def care_words(text: str) -> list[str]:
    return [m.group(0).strip() for m in _CARE_RX.finditer(_norm(text))][:4]


# phrases that mean the person (or someone they look after) is unwell without naming anything
_FEELING = re.compile(
    _WORD_L + r"(?:(?:i|we|he|she|they|mai|main|me|mujhe|mujhko|humko|hamein|unhe|unko|use|isko)\s+)?"
    r"(?:am|is|are|feel|feeling|feels|lag raha|lag rahi|lagta|ho raha|ho rahi|hota|hoti)\s+(?:very |bahut |so |quite |kind of |thoda |thodi )?"
    r"(?:bad|terrible|awful|horrible|worse|poorly|dull|shaky|tense|scared|afraid|low|helpless|hopeless|restless|uneasy|numb|dizzy|odd|strange|off|not okay|not ok|not fine|not good|"
    r"kharab|bura|buri|ajeeb|ajib|darr|dar|besharam)" + _WORD_R, re.I)
_WHO_UNWELL = re.compile(
    _WORD_L + r"(?:papa|pitaji|father|dad|mummy|maa|mother|mom|dadi|dada|dadaji|nani|nana|wife|husband|biwi|patni|pati|beta|beti|son|daughter|baby|bachcha|bacha|bacche|bhai|behen|sister|brother|"
    r"uncle|aunty|chacha|chachi|mama|mami|bua|fufa|friend|dost|neighbour|neighbor|padosi|patient)\s+(?:\S+\s+){0,3}"
    r"(?:bimar|bimaar|ill|sick|unwell|not well|theek nahi|thik nahi|thik nhi|theek nhi|haalat|halat|tabiyat|tabiat)" + _WORD_R, re.I)

# Anything the gate should never treat as a health message even when a weak care word (help, book, visit) appears.
NON_HEALTH_TASK = re.compile(
    _WORD_L + r"(?:homework|assignment|essay|poem|story|joke|recipe|flight|flights|ticket|tickets|hotel|train|bus|cab|taxi|movie|film|song|songs|gaana|match|score|cricket|ipl|football|stock|stocks|share market|"
    r"bitcoin|crypto|weather|mausam|code|coding|python|javascript|website|wifi|laptop|computer|charger|exam|syllabus|resume|cv|interview|salary|loan|emi|tax|gst|insurance claim|"
    r"translate|translation|capital of|president|prime minister|news|joke|riddle|math|maths|physics|chemistry|biology homework|pizza|burger|food swiggy|zomato|amazon|flipkart|"
    r"server|servers|software|database|logo|design|ui|ux|emoji|emojis|trailer|horoscope|zodiac|rashifal|rashi|astrology|antivirus|malware|management system|project ideas|studying|maths|stress test|load test|startup|business|app|apps|phone|"
    r"holiday|diwali|holi|eid|christmas|birthday|wedding|shopping|discount|netflix|youtube|instagram|whatsapp|facebook|twitter|game|games|pubg|ludo)" + _WORD_R, re.I)


_WEAK_RX = _alias_rx(sorted(_WEAK_GENERAL))


# a person-centred cue ("mujhe", "papa ko", "I have", "diagnosed", "patient") keeps a message medical even if it also mentions an everyday task
_PERSON_CUE = re.compile(_WORD_L + r"(?:mujhe|mujhko|mujko|humko|hamein|unko|unhe|isko|usko|ko|diagnosed|patient|positive|i have|i am|i got|he has|she has|has been|have been|ho gaya|ho gayi|hua hai)" + _WORD_R)


_VOCAB_TOKEN = re.compile(r"[^\s\d,.;:!?|।()\"'’‘“”\-/]+")
_dataset_vocab: Optional[dict] = None


def _dataset_tokens() -> dict:
    """Symptom cues derived from Tulsiandhare/Multilingual_medical_symptom_triage (pipeline/scripts/prepare_multilingual_triage.py).
    Only non-Latin-script tokens are used here: Latin symptom words are already covered by the lexicon."""
    global _dataset_vocab
    if _dataset_vocab is None:
        try:
            path = Path(__file__).resolve().parents[1] / "rules" / "dataset_vocab.json"
            toks = json.loads(path.read_text(encoding="utf-8")).get("tokens", {})
            _dataset_vocab = {t: v for t, v in toks.items() if v.get("lang") not in ("english", "hinglish")}
        except (OSError, ValueError):
            _dataset_vocab = {}
    return _dataset_vocab


def dataset_symptom_cues(text: str) -> list[str]:
    vocab = _dataset_tokens()
    return sorted({t for t in (w.lower() for w in _VOCAB_TOKEN.findall(text)) if t in vocab})


def health_signal(text: str) -> tuple[bool, str, list[ConditionMatch]]:
    """(is_health, why, conditions). A *strong* signal is a named condition or a first-person/third-person unwell statement;
    care words alone are weak (they are accepted only when no everyday-task word is present)."""
    t = _norm(text)
    if NON_HEALTH_TASK.search(t) and not _PERSON_CUE.search(t):
        return False, "", []  # "cancer zodiac sign", "stress test of the server", "hospital management system project ideas"
    conds = find_conditions(text)
    if conds:
        return True, f"condition:{conds[0].key}:{conds[0].matched}", conds
    if _FEELING.search(t) or _WHO_UNWELL.search(t):
        return True, "unwell-statement", []
    if _WEAK_RX.search(t) and not NON_HEALTH_TASK.search(t):
        return True, "weak-medical-word", []
    cw = care_words(text)
    if cw and not NON_HEALTH_TASK.search(t):
        return True, f"care-word:{cw[0]}", []
    cues = dataset_symptom_cues(text)
    if len(cues) >= 2:  # two symptom words from the dataset vocabulary in another script (Devanagari/Bengali/Telugu/Gujarati)
        return True, f"dataset-symptoms:{','.join(cues[:3])}", []
    return False, "", []
