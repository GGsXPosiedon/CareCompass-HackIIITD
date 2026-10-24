"""Context-aware intent + dialogue management (runs between the safety rules and the triage models).

What it does
  * Classifies the LATEST user message: greeting | general | health | answer | refusal | stop | frustration | resume
    (+ a `correction` flag). Rule based and deterministic; every pattern is auditable below.
  * Scopes the context: concepts are built turn by turn, later statements override earlier ones, and a message that
    reports a NEW problem does not inherit older symptoms. (The safety rules still see the whole user text.)
  * Counts only assistant messages that are real questions toward the follow-up budget.
  * Picks the next follow-up question from missing clinical slots (duration, temperature, anything else...).

What it never does: choose a care type, lower an emergency, or let tone/emotion change urgency. Emergencies are decided
by app/services/safety.py BEFORE this module is consulted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from ..schemas.external import TriageRequest
from ..schemas.internal import FactStatus
from .lexicon import detect_language, extract_concepts, group_of, normalize, resolve_language, strip_prefix

_RUNS = re.compile(r"(.)\1{2,}")


_NEG_PHRASE = re.compile(r"\b(?:i |we |he |she |they )?(?:do not|dont|don't|does not|doesnt|doesn't|did not|didnt|didn't|have no|has no|"
                         r"haven't|havent|hasn't|hasnt|there is no|there's no|no sign of|without any)\b (?:(?:have|had|got) )?(?:a |an |any |the )?")


def _n(text: str) -> str:
    """Normalised text for intent and concept extraction. 'I don't have a fever' becomes 'no fever' here; the red-flag
    rules use the plain normaliser (strict, immediate-cue negation only) and are not affected."""
    return _NEG_PHRASE.sub("no ", normalize(_RUNS.sub(r"\1", text.lower())))


# ---------------------------------------------------------------- patterns (on normalised text) --------
def _rx(*pats: str) -> re.Pattern:
    return re.compile("|".join(f"(?:{p})" for p in pats))


GREETING = _rx(r"^(hi+|hello+|hey+|hii+|hlo|helo|namaste|namaskar|good (morning|evening|afternoon)|नमस्ते|नमस्कार|हेलो)\b")
STOP = _rx(r"\b(stop|bas|enough|quit|exit|forget it|leave it|rehne do|rahne do|band karo|band kar do)\b", r"बस कर|रहने दो|बंद करो|छोड़ो")
REFUSAL = _rx(
    r"\b(nahi|not|no|dont|don't|never)\b(?: \S+){0,4} \b(chahiye|chaiye|chahie|chahta|chahti|want|need|require|book|karwana|karna)\b",
    r"\bno need\b", r"\bi am fine\b", r"\bi m fine\b", r"\bim fine\b", r"\b(mai|me)\b(?: \S+){0,3} \b(theek|thik)\b",
    r"\bakel[ea]\b", r"\bekel[ea]\b", r"leave me alone", r"नहीं चाहिए", r"नही चाहिए", r"मैं ठीक", r"मै ठीक", r"अकेल",
)
FRUSTRATION = _rx(
    r"bhaad me", r"bhad me", r"\bchup\b", r"shut up", r"\bstupid\b", r"\buseless\b", r"\bbakwas\b", r"\bbekar\b", r"\bidiot\b",
    r"go away", r"get lost", r"\bpagal\b", r"not understanding", r"samajh nahi aa raha", r"बकवास", r"बेकार", r"भाड़ में", r"चुप",
)
CORRECTION = _rx(r"\b(sorry|actually|wait|galat|i meant|mera matlab|correction|mistake|nahi nahi|no no|oops)\b", r"गलत|मेरा मतलब|माफ़")
RESUME = _rx(r"\b(ok|okay|theek hai|thik hai|chalo|changed my mind|mann badal|mind change|book it|book kar|bhej do|haan chahiye)\b",
             r"ठीक है|चलो|मन बदल")
CONTINUING = _rx(r"\b(aur|also|and|bhi|saath|along|plus|ab bhi|still)\b", r"और|भी|साथ")
TIMING_NOW = re.compile(r"\bright now\b|\bnow\b|\bimmediate\w*|\bright away\b|\basap\b|\burgent\w*|\babhi\b(?! se)|\bturant\b|\bjaldi\b|\bfauran\b|अभी|तुरंत|जल्दी", re.I)
TIMING_TODAY = re.compile(r"\blater today\b|(?<!since )\btoday\b|\baaj\b(?! se)|\bshaam\b|\bevening\b|\bafternoon\b|\bdopahar\b|\btonight\b|\braat\b|in a few hours|aaj baad|आज(?! से)|शाम|दोपहर", re.I)
TIMING_LATER = re.compile(r"\btomorrow\b|\bkal\b(?! se)|\bparso\b|\bschedul\w*|next week|later this week|कल(?! से)|परसों|शेड्यूल", re.I)
UNSURE = _rx(r"pata nahi", r"not sure", r"don't know", r"dont know", r"पता नहीं")
YES = _rx(r"^(yes|yeah|yep|haan|han|ha|haa|हाँ|हां)\b")
NO = _rx(r"^(no|nope|nahi|नहीं|नही)\b")
RELATION = re.compile(r"\b(papa|pitaji|father|dad|mummy|maa|mother|mom|son|beta|beti|daughter|wife|husband|biwi|patni|pati|baby|infant|child|"
                      r"bachcha|bacche|bacha|dadaji|dadi|nani|nana|grandfather|grandmother|brother|bhai|sister|behen)\b|बच्चा|पापा|मम्मी|माँ")
AGE = re.compile(r"\b(\d{1,3}) ?(years?|yrs?|saal|sal|months?|mahine)\b|साल|महीने")
TEMP = re.compile(r"\b(9[4-9]|10[0-9]|11[0-1])( \d)?\b|\b(3[5-9]|4[0-2]) ?(degree|deg|celsius|c)\b")
NUM = r"(?:\d+|ek|do|teen|char|chaar|paanch|panch|chhe|saat|aath|nau|das|one|two|three|four|five|six|seven|a couple of|few|kuch)"
DURATION = re.compile(rf"\b{NUM} ?(din|days?|hours?|ghante|hafte|weeks?|mahine|months?)\b|\b(kal se|kal raat|parso|since (yesterday|last (night|week)|morning)|"
                      r"aaj|today|subah se|raat se|abhi)\b|दिन|घंटे|हफ्ते|कल से|आज|अभी")
SEVERITY = re.compile(r"\b(mild|moderate|severe|halka|halki|madhyam|tez|bahut|zyada|unbearable|\d{1,2} ?(?:/|out of) ?10)\b|तेज|हल्का|बहुत")

# vague but real care requests ("doctor chahiye", "I want to book something"): triage proceeds and asks what is needed
CARE_REQUEST = re.compile(r"\b(doctor|dr|nurse|medic|paramedic|caregiver|care|help|book|booking|appointment|visit|checkup|ambulance|"
                          r"treatment|medicine|dawai|dawa)\b|डॉक्टर|नर्स|सहायता|मदद|इलाज|दवा")

# explicit service requests: the user already said what they want, so no symptom questions are asked
SERVICE_GROUPS = {"nursing", "lab", "consult"}

# ---------------------------------------------------------------- symptom names / slots ----------------
# Any wording that may describe a person in trouble must never be treated as chit-chat:
# it proceeds to triage (and to the LLM safety screen) instead of the generic reply.
URGENT_WORDS = re.compile(
    r"\b(breath\w*|saans|pulse|heart|dil|blood|khoon|bleed\w*|unconscious|behosh|faint\w*|collaps\w*|seizure|fits?|choking|chok\w+|poison\w*|"
    r"overdose|ambulance|emergency|dying|die|dead|burn\w*|drown\w*|accident|sick|ill|hurt|injur\w*|pain|dard|wound|unwell|"
    r"suicid\w*|kill\w*|paralys\w*|stroke|swell\w*|vomit\w*|ulti|fell|fall|gir|help|bachao|marr?\w*|sans)\b"
    r"|\u0938\u093e\u0901?\u0938|\u0938\u093e\u0902\u0938|\u092c\u0947\u0939\u094b\u0936|\u0916\u0942\u0928|\u0926\u0930\u094d\u0926", re.I)

# Broad everyday-complaint vocabulary (en / Hinglish / Hindi): recognises that someone is describing a health problem even
# when no routing concept exists for it (dizziness, sore throat, rash, urine burning...). Used for recognition + naming only.
GENERAL_SYMPTOMS = re.compile(
    r"\b(dizz\w*|chakkar|lightheaded|vertigo|throat|gala|gale|sardi|zukam|zukaam|cold|runny nose|sneez\w*|chheenk\w*|rash|itch\w*|khujli|khujlee|daane|skin|"
    r"allerg\w*|tooth\w*|dant|kaan|ear|eye|eyes|aankh|aankhon|urin\w*|peshab|burning|jalan|constipat\w*|kabz|acidity|heartburn|nausea|mitli|swell\w*|"
    r"sujan|cramp\w*|period|periods|bp|sugar|diabetes|thyroid|joint|joints|jodon|jodo|kandhe|shoulder|neck|gardan|leg|legs|pair|haath|hand|ankle|sprain\w*|"
    r"injur\w*|chot|cut|wound|ghav|fractur\w*|ache|aches|hurts?|hurting|dukh\w*|tired|fatigue|weak\w*|kamzor\w*|sick|bimar\w*|unwell|"
    r"naak|nose|nostril|fever|bukhar|cough|khansi|breathless\w*|insomnia|neend|anxiety|ghabrahat|stress|palpitation\w*|dhadkan)\b"
    r"|चक्कर|गला|गले|सर्दी|जुकाम|खुजली|त्वचा|दांत|कान|आंख|आँख|पेशाब|जलन|कब्ज|सूजन|जोड़ों|कंधे|गर्दन|पैर|हाथ|चोट|घाव|कमज़ोर|कमजोर|थक|बीमार|बुखार|खांसी|घबराहट|धड़कन|नाक", re.I)

OTHER_NAMES = [  # (stem regex, names per language) - readable names for complaints that have no routing concept
    (re.compile(r"throat|gala|gale|गला|गले"), {"en": "sore throat", "hi": "गले की तकलीफ़", "hinglish": "gale ki taklif"}),
    (re.compile(r"dizz|chakkar|lightheaded|vertigo|चक्कर"), {"en": "dizziness", "hi": "चक्कर", "hinglish": "chakkar"}),
    (re.compile(r"skin|rash|itch|khujli|khujlee|daane|allerg|त्वचा|खुजली"), {"en": "skin problem", "hi": "त्वचा की परेशानी", "hinglish": "skin ki pareshani"}),
    (re.compile(r"sardi|zukam|zukaam|runny|sneez|chheenk|naak|nose|नाक|सर्दी|जुकाम"), {"en": "cold / runny nose", "hi": "सर्दी-जुकाम", "hinglish": "sardi-zukam"}),
    (re.compile(r"urin|peshab|jalan|burning|पेशाब|जलन"), {"en": "urinary problem", "hi": "पेशाब की परेशानी", "hinglish": "peshab ki taklif"}),
    (re.compile(r"tooth|dant|दांत"), {"en": "toothache", "hi": "दांत का दर्द", "hinglish": "dant ka dard"}),
    (re.compile(r"\bear\b|kaan|कान"), {"en": "ear problem", "hi": "कान की तकलीफ़", "hinglish": "kaan ki taklif"}),
    (re.compile(r"eye|aankh|आंख|आँख"), {"en": "eye problem", "hi": "आँख की तकलीफ़", "hinglish": "aankh ki taklif"}),
    (re.compile(r"joint|jodo|जोड़ों|shoulder|kandhe|कंधे|neck|gardan|गर्दन|\bleg|pair|पैर|haath|hand|हाथ|ankle"), {"en": "joint / limb pain", "hi": "जोड़ों/अंगों का दर्द", "hinglish": "jodon/ang ka dard"}),
    (re.compile(r"injur|chot|cut|wound|ghav|fractur|sprain|चोट|घाव"), {"en": "injury", "hi": "चोट", "hinglish": "chot"}),
]
_COVERED_BY_CONCEPTS = {"ache", "aches", "hurt", "hurts", "hurting", "tired", "fatigue", "sick", "unwell", "fever", "bukhar", "cough", "khansi", "pain", "dard",
                        "bimar", "kamzor", "weak", "weakness", "dukh", "bimaar"}

# things people ask to have CHECKED or tested, not complaints: never turned into 'how long have you had the bp?'
_CHECK_WORDS = {"bp", "sugar", "diabetes", "thyroid", "period", "periods", "cold"}

BODY_PAIN = {
    "knee_pain": re.compile(r"\bknee|ghutn|घुटन"),
    "back_pain": re.compile(r"\bback ?(pain|ache)|\bback (?:hurts?|is (?:hurting|paining|sore))|backache|peeth|kamar|पीठ|कमर"),
    "headache": re.compile(r"headache|head ache|head (?:hurts?|pain|is (?:hurting|paining)|is aching)|migraine|\bsir (dard|me dard)|\bsar (dard|me dard)|सिरदर्द|(?:सिर|सर) (?:में )?दर्द"),
    "stomach_pain": re.compile(r"stomach|abdom|belly|tummy|\bpet (dard|me dard)|पेट"),
    "bleeding": re.compile(r"nose ?bleed|\bbleed\w*|\bkhoon\b|\bblood\b|\u0916\u0942\u0928|\bcut\b"),
}
NAMES = {
    "fever": {"en": "fever", "hi": "बुखार", "hinglish": "bukhar"},
    "cough": {"en": "cough", "hi": "खांसी", "hinglish": "khansi"},
    "weakness": {"en": "weakness", "hi": "कमज़ोरी", "hinglish": "kamzori"},
    "pain": {"en": "pain", "hi": "दर्द", "hinglish": "dard"},
    "stomach_upset": {"en": "stomach upset", "hi": "पेट की परेशानी", "hinglish": "pet ki pareshani"},
    "knee_pain": {"en": "knee pain", "hi": "घुटने का दर्द", "hinglish": "ghutne ka dard"},
    "back_pain": {"en": "back pain", "hi": "पीठ का दर्द", "hinglish": "peeth ka dard"},
    "headache": {"en": "headache", "hi": "सिरदर्द", "hinglish": "sir dard"},
    "bleeding": {"en": "bleeding", "hi": "खून बहना", "hinglish": "khoon behna"},
    "stomach_pain": {"en": "stomach pain", "hi": "पेट का दर्द", "hinglish": "pet ka dard"},
}
HINTS = {
    "fever": {"en": "cough, breathing trouble, vomiting or a rash", "hi": "खांसी, साँस में तकलीफ़, उल्टी या दाने", "hinglish": "khansi, saans mein taklif, ulti ya daane"},
    "knee_pain": {"en": "swelling, redness, fever or trouble walking", "hi": "सूजन, लालपन, बुखार या चलने में दिक्कत", "hinglish": "sujan, laalpan, bukhar ya chalne mein dikkat"},
    "back_pain": {"en": "numbness, leg weakness or fever", "hi": "सुन्नपन, पैरों में कमज़ोरी या बुखार", "hinglish": "sunnpan, pairon mein kamzori ya bukhar"},
    "headache": {"en": "vomiting, blurred vision or fever", "hi": "उल्टी, धुंधला दिखना या बुखार", "hinglish": "ulti, dhundhla dikhna ya bukhar"},
    "stomach_pain": {"en": "vomiting, loose motions or fever", "hi": "उल्टी, दस्त या बुखार", "hinglish": "ulti, dast ya bukhar"},
    "bleeding": {"en": "dizziness, weakness or a fall", "hi": "चक्कर, कमज़ोरी या गिरना", "hinglish": "chakkar, kamzori ya girna"},
    "default": {"en": "fever, vomiting or breathing trouble", "hi": "बुखार, उल्टी या साँस में तकलीफ़", "hinglish": "bukhar, ulti ya saans mein taklif"},
}
QUESTIONS = {
    "duration": {"en": "How long have you had the {symptom}?", "hi": "{symptom} कब से है?", "hinglish": "{symptom} kab se hai?"},
    "temperature": {"en": "Have you checked the temperature? If yes, what does it show?", "hi": "क्या आपने तापमान नापा? अगर हाँ, तो कितना है?",
                    "hinglish": "Kya aapne temperature naapa? Agar haan, to kitna hai?"},
    "bleed_check": {"en": "How heavy is the bleeding? Has it slowed or stopped, or is it still heavy after 10 minutes of pressing?",
                    "hi": "खून कितना बह रहा है? क्या वह कम हुआ या रुक गया, या 10 मिनट दबाने के बाद भी तेज़ है?",
                    "hinglish": "Khoon kitna beh raha hai? Kya kam hua ya ruk gaya, ya 10 minute dabane ke baad bhi tez hai?"},
    "timing": {"en": "When do you need the visit? Right now, later today, or can it be scheduled?",
               "hi": "विज़िट कब चाहिए? अभी, आज बाद में, या कल/शेड्यूल कर सकते हैं?",
               "hinglish": "Visit kab chahiye? Abhi, aaj baad mein, ya kal/schedule kar sakte hain?"},
    "associated": {"en": "Is there anything else along with it, such as {hints}?", "hi": "क्या इसके साथ कुछ और भी है, जैसे {hints}?",
                   "hinglish": "Kya iske saath kuch aur bhi hai, jaise {hints}?"},
}
DURATION_OPTIONS = {"en": ["Since today", "1–2 days", "3 days or more"], "hi": ["आज से", "1–2 दिन से", "3 दिन या ज़्यादा"],
                    "hinglish": ["Aaj se", "1–2 din se", "3 din ya zyada"]}
BLEED_OPTIONS = {"en": ["Slow / stopped", "Still heavy", "Not sure"], "hi": ["कम / रुक गया", "अभी भी तेज़", "पता नहीं"],
                 "hinglish": ["Kam / ruk gaya", "Abhi bhi tez", "Pata nahi"]}
TIMING_OPTIONS = {"en": ["Right now", "Later today", "Tomorrow / schedule it"], "hi": ["अभी", "आज बाद में", "कल / शेड्यूल"],
                  "hinglish": ["Abhi", "Aaj baad mein", "Kal / schedule"]}
SLOT_ORDER = {"bleeding": ["bleed_check"], "fever": ["duration", "temperature"], "pain": ["duration", "associated"], "default": ["duration", "associated"]}

REPLIES = {
    "greeting": {"en": "Hello! Tell me what is troubling you or someone in your family, and I will help find the right care.",
                 "hi": "नमस्ते! बताइए आपको या आपके परिवार में किसी को क्या तकलीफ़ है, मैं सही देखभाल ढूँढने में मदद करूँगा।",
                 "hinglish": "Namaste! Bataiye aapko ya aapke parivar mein kisi ko kya taklif hai, main sahi care dhoondhne mein madad karunga."},
    "general": {"en": "I can help with health and home-care needs. Could you tell me in a few words what is wrong, or who is unwell?",
                "hi": "मैं स्वास्थ्य और घर पर देखभाल में मदद कर सकता हूँ। कृपया थोड़े शब्दों में बताइए कि क्या तकलीफ़ है या कौन बीमार है।",
                "hinglish": "Main health aur ghar par care mein madad kar sakta hoon. Kripya thode shabdon mein bataiye ki kya taklif hai ya kaun bimaar hai."},
    "refusal": {"en": "Understood, I won't book anything. If you change your mind I'm here. If there is trouble breathing, chest pain or confusion, please call 112.",
                "hi": "समझ गया, मैं कुछ बुक नहीं करूँगा। मन बदले तो मैं यहाँ हूँ। अगर साँस लेने में तकलीफ़, सीने में दर्द या भ्रम हो तो कृपया 112 पर कॉल करें।",
                "hinglish": "Samajh gaya, main kuch book nahi karunga. Mann badle to main yahan hoon. Agar saans lene mein taklif, seene mein dard ya confusion ho to kripya 112 par call karein."},
    "frustration": {"en": "I'm sorry if I frustrated you. I'll stop here, and you can message me whenever you want help.",
                    "hi": "अगर मैंने आपको परेशान किया तो माफ़ कीजिए। मैं यहीं रुकता हूँ, जब भी मदद चाहिए मुझे लिख दीजिएगा।",
                    "hinglish": "Agar maine aapko pareshan kiya to maaf kijiye. Main yahin rukta hoon, jab bhi madad chahiye mujhe likh dijiyega."},
    "stop": {"en": "Okay, I'll stop here. You can message me whenever you need health or home care. If it is an emergency, call 112.",
             "hi": "ठीक है, मैं यहीं रुकता हूँ। जब भी स्वास्थ्य या घर पर देखभाल चाहिए, मुझे लिख दीजिएगा। आपातकाल में 112 पर कॉल करें।",
             "hinglish": "Theek hai, main yahin rukta hoon. Jab bhi health ya ghar par care chahiye, mujhe likh dijiyega. Emergency mein 112 par call karein."},
}
NON_QUESTION_REPLIES = {t for kind in REPLIES.values() for t in kind.values()}
REDIRECT_LIKE = re.compile(r"how can (i|we) help|what is wrong|tell me what|kya madad|kaise madad|क्या मदद|सही देखभाल|what care do you need|"
                           r"i didn'?t (quite )?understand|how can we help", re.I)
LEGACY_GENERIC = {"Happy to help. What kind of care do you need?", "मैं मदद करूँगा। आपको किस तरह की देखभाल चाहिए?",
                  "Zaroor madad karunga. Aapko kis tarah ki care chahiye?"}


def _template_rx() -> list[tuple[str, re.Pattern]]:
    out = []
    for slot, q in QUESTIONS.items():
        for lang in ("en", "hi", "hinglish"):
            pat = re.escape(q[lang]).replace(re.escape("{symptom}"), ".+").replace(re.escape("{hints}"), ".+")
            out.append((slot, re.compile("^" + pat + "$")))
    return out


_TEMPLATES = _template_rx()


def slot_of(assistant_text: str) -> Optional[str]:
    t = assistant_text.strip()
    return next((slot for slot, rx in _TEMPLATES if rx.match(t)), None)


def is_real_question(assistant_text: str) -> bool:
    """True only for an assistant message that genuinely asks the user something we need answered."""
    t = assistant_text.strip()
    if not t or t in NON_QUESTION_REPLIES:
        return False
    if slot_of(t) or t in LEGACY_GENERIC:
        return True
    if REDIRECT_LIKE.search(t):
        return False
    return t.endswith(("?", "？"))


# ---------------------------------------------------------------- analysis ----------------------------
@dataclass
class Analysis:
    act: str = "health"
    correction: bool = False
    new_topic: bool = False
    scoped_user: list = field(default_factory=list)       # user turns that feed concept extraction
    scoped_history: list = field(default_factory=list)    # [{'role','content'}] shown to the LLM nodes
    concepts: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    questions_asked: int = 0
    asked_slots: list = field(default_factory=list)
    known_slots: dict = field(default_factory=dict)
    symptoms: list = field(default_factory=list)          # ordered symptom keys (body pain names first)
    service_request: bool = False
    language: str = "en"


def _segments(hist: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """Split the history into episodes. A boundary is any assistant turn that is NOT a real question
    (greeting, redirect, decision, refusal ack...): after it, the conversation is about whatever the user says next."""
    segs: list[list[tuple[str, str]]] = [[]]
    for role, content in hist:
        segs[-1].append((role, content))
        if role == "assistant" and not is_real_question(content):
            segs.append([])
    return segs


def classify_turn(text: str, awaiting_answer: bool, concepts: dict) -> tuple[str, bool]:
    t = _n(text)
    present = {c for c, s in concepts.items() if s == FactStatus.PRESENT}
    has_health = bool(present - {"home_visit_request"}) or any(rx.search(t) for rx in BODY_PAIN.values()) or bool(CARE_REQUEST.search(t)) or bool(URGENT_WORDS.search(t)) or bool(GENERAL_SYMPTOMS.search(t))
    service = any(group_of(c) in SERVICE_GROUPS for c in present)
    correction = bool(CORRECTION.search(t))
    if has_health and service and REFUSAL.search(t):
        return "health", correction  # "not a lab test, a doctor": a changed request, not a refusal
    if STOP.search(t) and not has_health:
        return "stop", correction
    if FRUSTRATION.search(t):
        return "frustration", correction
    if REFUSAL.search(t):
        return "refusal", correction
    if has_health:
        return "health", correction
    if awaiting_answer:
        return "answer", correction
    if GREETING.search(t):
        return "greeting", correction
    return "general", correction


def _health_concepts(user_turns: list[str]) -> set:
    out: set = set()
    for t in user_turns:
        c, _ = extract_concepts(_n(t))
        out |= {k for k, st in c.items() if st == FactStatus.PRESENT and k != "home_visit_request"}
        out |= {k for k, rx in BODY_PAIN.items() if rx.search(_n(t))}
    return out


def _symptoms(text_norm_turns: list[str], concepts: dict) -> list[str]:
    out: list[str] = []
    for t in text_norm_turns:
        for key, rx in BODY_PAIN.items():
            if rx.search(t) and key not in out:
                out.append(key)
    for c in ("fever", "cough", "stomach_upset", "weakness", "pain"):
        if concepts.get(c) == FactStatus.PRESENT and c not in out and not (c == "pain" and out):
            out.append(c)
    for t in text_norm_turns:  # an everyday complaint with no routing concept: keep it, named in readable words
        m = next((x for x in GENERAL_SYMPTOMS.finditer(t)
                  if x.group(0).lower() not in _CHECK_WORDS and not any(x.group(0).lower().startswith(c) for c in _COVERED_BY_CONCEPTS)), None)
        if m:
            nm = next((n for rx, n in OTHER_NAMES if rx.search(m.group(0))), None)
            key = "other:" + (m.group(0))
            if nm is not None and key not in out and not any(k.startswith("other:") for k in out):
                out.append(key)
            break
    return out


def _fill_slots(messages: list[tuple[str, str]]) -> dict:
    known: dict = {}
    pending = None
    for role, content in messages:
        if role == "assistant":
            pending = slot_of(content)
            continue
        t = _n(content)
        if TEMP.search(t):
            known["temperature"] = TEMP.search(t).group(0)
        if DURATION.search(t):
            known["duration"] = DURATION.search(t).group(0)
        tm = "now" if TIMING_NOW.search(t) else "today" if TIMING_TODAY.search(t) else "later" if TIMING_LATER.search(t) else None
        if tm and pending != "duration":   # "Abhi"/"Aaj" answering "how long?" is a duration, not a visit time
            known["timing"] = tm
        if SEVERITY.search(t):
            known["severity"] = SEVERITY.search(t).group(0)
        if pending and UNSURE.search(t):
            known[pending] = "unknown"
        if pending == "temperature" and NO.search(t):
            known["temperature"] = "not_measured"
        if pending == "bleed_check" and len(t.split()) >= 1:
            known["bleed_check"] = True
        if pending == "associated" and (YES.search(t) or NO.search(t) or len(t.split()) >= 2):
            known["associated"] = True
        if pending == "duration" and "duration" not in known and len(t.split()) <= 4:
            known["duration"] = "stated"
        pending = None
    return known


def analyze(req: TriageRequest) -> Analysis:
    hist = [(t.role, strip_prefix(t.content) if t.role == "user" else t.content) for t in req.conversation_history if t.content]
    latest = strip_prefix(req.user_input)
    segs = _segments(hist)
    current = segs[-1]                      # turns since the last non-question assistant message
    awaiting = bool(hist) and hist[-1][0] == "assistant" and is_real_question(hist[-1][1])
    latest_c, _ = extract_concepts(_n(latest))
    act, correction = classify_turn(latest, awaiting, latest_c)

    scope: list[tuple[str, str]]
    new_topic = False
    n_latest = _n(latest)
    own = {c for c, st in latest_c.items() if st == FactStatus.PRESENT and c != "home_visit_request"} | \
        {k for k, rx in BODY_PAIN.items() if rx.search(n_latest)}
    refusal_ack = bool(hist) and hist[-1][0] == "assistant" and any(hist[-1][1] == REPLIES[k][l] for k in ("refusal", "frustration", "stop") for l in ("en", "hi", "hinglish"))
    if refusal_ack and RESUME.search(n_latest) and not own:
        # "ok, book it" right after a refusal: resume the most recent episode that actually had a health problem in it
        scope = next((sg for sg in reversed(segs[:-1]) if _health_concepts([c for r, c in sg if r == "user"])), [])
        act = "health" if scope else act
    elif act in ("health", "answer") and not CONTINUING.search(n_latest):
        if awaiting and slot_of(hist[-1][1]) in ("associated", "bleed_check"):
            scope = current  # a reply to OUR slot question, even one that names another symptom ("ulti bhi hai")
        elif awaiting:
            earlier = _health_concepts([c for r, c in current if r == "user"])
            # the user ignored our question and reported something unrelated: do not drag the old problem along
            new_topic = bool(own and earlier and not (own & earlier))
            scope = [] if new_topic else current
        else:
            scope, new_topic = [], bool(current)   # a fresh report: earlier episodes must not bleed into this one
    else:
        scope = current
    messages = list(scope) + [("user", latest)]
    user_turns = [c for r, c in messages if r == "user"]

    merged: dict = {}
    evidence: dict = {}
    for turn in user_turns:                 # chronological overlay: later statements override earlier ones
        c, e = extract_concepts(_n(turn))
        merged.update(c)
        evidence.update(e)
    norm_turns = [_n(t) for t in user_turns]
    symptoms = _symptoms(norm_turns, merged)
    present = {c for c, s in merged.items() if s == FactStatus.PRESENT}
    asked = [c for r, c in messages if r == "assistant" and is_real_question(c)]
    lang = resolve_language(req.language, *[c for r, c in hist if r == 'user'], latest)
    return Analysis(
        act=act, correction=correction, new_topic=new_topic, scoped_user=user_turns,
        scoped_history=[{"role": r, "content": c} for r, c in scope],
        concepts=merged, evidence=evidence, questions_asked=len(asked),
        asked_slots=[s for s in (slot_of(c) for c in asked) if s],
        known_slots=_fill_slots(messages), symptoms=symptoms,
        service_request=any(group_of(c) in SERVICE_GROUPS for c in present), language=lang,
    )


# ---------------------------------------------------------------- decisions ---------------------------
@dataclass
class DialogueDecision:
    kind: str                       # reply | ask | proceed
    message: Optional[str] = None
    options: Optional[list] = None
    slot: Optional[str] = None
    reason: str = ""


def _symptom_text(key: str, lang: str) -> str:
    if key.startswith("other:"):
        w = key[6:]
        return next((n[lang] for rx, n in OTHER_NAMES if rx.search(w)), w)
    return NAMES.get(key, NAMES["pain"])[lang]


def next_slot_question(a: Analysis) -> Optional[DialogueDecision]:
    if not a.symptoms:
        return None
    main = a.symptoms[0]
    order = SLOT_ORDER["fever" if main == "fever" else "bleeding" if main == "bleeding" else "pain" if main.endswith("pain") or main == "headache" else "default"]
    lang = a.language
    for slot in order:
        if slot in a.asked_slots or slot in a.known_slots:
            continue
        text = QUESTIONS[slot][lang].format(symptom=_symptom_text(main, lang), hints=HINTS.get(main, HINTS["default"])[lang])
        return DialogueDecision("ask", text, DURATION_OPTIONS[lang] if slot == "duration" else BLEED_OPTIONS[lang] if slot == "bleed_check" else None, slot, f"missing slot: {slot}")
    return None


def decide(a: Analysis, max_questions: int, adaptive: bool = True) -> DialogueDecision:
    lang = a.language
    if a.act in ("greeting", "general", "refusal", "frustration", "stop"):
        return DialogueDecision("reply", REPLIES[a.act][lang], reason=f"intent={a.act}: no triage, no caregivers")
    # Start asking only when the message lacks the basics (how long) and nothing was asked yet; once OUR slot question is open,
    # finish the core slots. An answer to the generic 'what care do you need?' question goes straight to routing.
    # A message that already says how long ("papa ko do din se bukhar hai aur khansi bhi") is specific enough to route.
    started = bool(a.asked_slots) or (a.questions_asked == 0 and "duration" not in a.known_slots)
    if adaptive and started and not a.service_request and a.questions_asked < max_questions:
        q = next_slot_question(a)
        if q:
            return q
    return DialogueDecision("proceed", reason=f"intent={a.act}")


def timing_of(a) -> str | None:
    """User-stated urgency of the visit: 'now' | 'today' | 'later', or None when unstated/unsure."""
    v = (a.known_slots or {}).get("timing") if a is not None else None
    return v if v in ("now", "today", "later") else None


def timing_question(a: Analysis) -> DialogueDecision:
    lang = a.language
    return DialogueDecision("ask", QUESTIONS["timing"][lang], TIMING_OPTIONS[lang], "timing", "visit timing unknown")


def effective_timing(a) -> tuple[str, str]:
    """(timing, source). The user's own words win. Otherwise we do not ask: a visit is assumed 'today' (that is what the
    organiser's same_day label means), and 'now' when the user describes the problem as severe/unbearable. Criticalness
    here only decides WHO IS AVAILABLE, never the care type or urgency label, and it never lowers anything."""
    stated = timing_of(a)
    if stated:
        return stated, "stated"
    sev = str((a.known_slots or {}).get("severity", "")) if a is not None else ""
    m = re.match(r"(\d{1,2}) ?(?:/|out of) ?10", sev)
    if sev and ((m and int(m.group(1)) >= 7) or re.search(r"severe|tez|bahut|zyada|unbearable|तेज|बहुत", sev)):
        return "now", "severity"
    return "today", "default"
