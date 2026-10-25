"""Writes backend/app/rules/pathways.json (the deterministic symptom pathways). UNREVIEWED demo content.
Edit the content here (or the JSON directly), then: python pipeline/scripts/build_pathways.py
Sources of the structure: WHO IMCI-style danger signs, NHS 111-style pathways (question tree -> fixed disposition), MoHFW dengue warning signs."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "backend" / "app" / "rules" / "pathways.json"
def T(en, hg, hi): return {"en": en, "hinglish": hg, "hi": hi}
YES = T("Yes", "Haan", "हाँ"); NO = T("No", "Nahi", "नहीं"); UNS = T("Not sure", "Pata nahi", "पता नहीं")
def Q(id, text, opts=None, danger=False):
    return {"id": id, "text": text, "danger": danger, "options": opts or [{"id": "yes", "label": YES}, {"id": "no", "label": NO}, {"id": "unsure", "label": UNS}]}
def O(id, en, hg, hi): return {"id": id, "label": T(en, hg, hi)}
def R(when, disp, care, urg, why, advice=None):
    r = {"when": when, "disposition": disp, "care_type": care, "urgency": urg, "why": why}
    if advice: r["advice"] = advice
    return r
EM = ("emergency", "emergency_112", "emergency")
DEN = ["yes", "unsure"]
P = []

P.append({"id": "fever", "title": T("Fever", "Bukhar", "बुखार"),
 "cues": [r"\bfever\b", r"\btemperature\b", r"\bbukh[ae]r\b", r"\btaap\b", r"बुखार", r"ज्वर", r"\bchills\b", r"\bdengue\b", r"\bmalaria\b", r"\btyphoid\b"],
 "questions": [
  Q("danger", T("Is there trouble breathing, confusion or unusual sleepiness, a stiff neck, a seizure, bluish lips, or a rash that does not fade when pressed?", "Kya saans lene mein taklif, uljhan ya bahut neend, gardan akadna, daura, hoth neele ya aisa daane hain jo dabane par nahi jaate?", "क्या साँस लेने में तकलीफ़, उलझन या बहुत नींद, गर्दन अकड़ना, दौरा, नीले होंठ या दबाने पर न मिटने वाले दाने हैं?"), danger=True),
  Q("bleed", T("Any bleeding (gums, nose, black stool), severe belly pain, or repeated vomiting?", "Kya khoon aana (masoodhe, naak, kala potty), pet mein tez dard ya baar-baar ulti hai?", "क्या खून आना (मसूड़े, नाक, काला मल), पेट में तेज़ दर्द या बार-बार उल्टी है?")),
  Q("duration", T("How many days has the fever lasted?", "Bukhar kitne din se hai?", "बुखार कितने दिन से है?"), [O("short", "Less than 2 days", "2 din se kam", "2 दिन से कम"), O("mid", "2 to 4 days", "2 se 4 din", "2 से 4 दिन"), O("long", "5 days or more", "5 din ya zyada", "5 दिन या ज़्यादा")]),
  Q("fluids", T("Is the person drinking fluids and passing urine normally?", "Kya paani pi rahe hain aur peshab normal hai?", "क्या पानी पी रहे हैं और पेशाब सामान्य है?"))],
 "rules": [
  R({"danger": DEN}, *EM, T("Fever with a danger sign can be meningitis, sepsis or severe infection.", "Bukhar ke saath khatre ka lakshan gambhir sankraman ho sakta hai.", "बुखार के साथ खतरे का लक्षण गंभीर संक्रमण हो सकता है।")),
  R({"bleed": DEN}, "urgent", "paramedic_home_visit", "same_day", T("Fever with bleeding or severe belly pain needs same-day examination (dengue warning signs).", "Bukhar ke saath khoon ya tez pet dard ka aaj hi check zaroori hai (dengue ke warning signs).", "बुखार के साथ खून या तेज़ पेट दर्द की आज ही जाँच ज़रूरी है (डेंगू के चेतावनी संकेत)।")),
  R({"fluids": ["no"]}, "urgent", "paramedic_home_visit", "same_day", T("Not drinking or passing urine risks dehydration.", "Paani na peena ya peshab kam hona dehydration ka khatra hai.", "पानी न पीना या पेशाब कम होना निर्जलीकरण का खतरा है।")),
  R({"duration": ["long"]}, "urgent", "teleconsultation", "same_day", T("Fever for 5 days or more needs a doctor and usually blood tests.", "5 din ya zyada ka bukhar doctor aur aksar blood test maangta hai.", "5 दिन या ज़्यादा का बुखार डॉक्टर और अक्सर ब्लड टेस्ट माँगता है।")),
  R({"duration": ["mid"]}, "routine", "teleconsultation", "scheduled", T("Fever for 2-4 days: book a doctor consult within a day or two.", "2-4 din ka bukhar: ek-do din mein doctor se consult lein.", "2-4 दिन का बुखार: एक-दो दिन में डॉक्टर से परामर्श लें।")),
  R({"duration": ["short"]}, "self_care", "teleconsultation", "scheduled", T("Short fever with no warning signs can usually be managed at home.", "Kam din ka bukhar bina warning signs ke aam taur par ghar par sambhal sakte hain.", "कम दिन का बुखार बिना चेतावनी संकेत के आम तौर पर घर पर संभाला जा सकता है।"),
    T("Rest and stay comfortable. Follow any fluid restrictions or care plan given by your doctor. Seek care if fever passes 3 days or any warning sign appears.", "Aaram karein aur aaraamdayak kapde pehnein. Paani ki pabandi ya doctor ka care plan ho to usi ko follow karein. 3 din se zyada ya koi warning sign ho to doctor dikhayen.", "आराम करें और आरामदायक कपड़े पहनें। पानी की पाबंदी या डॉक्टर की देखभाल योजना हो तो उसका पालन करें। 3 दिन से ज़्यादा या कोई चेतावनी संकेत हो तो डॉक्टर को दिखाएँ।"))]})

P.append({"id": "cough_breathing", "title": T("Cough or breathing", "Khansi ya saans", "खाँसी या साँस"),
 "cues": [r"\bcough\b", r"\bkhansi\b", r"खांसी", r"खाँसी", r"\bbreath", r"\bsaans\b", r"साँस", r"सांस", r"\bwheez", r"\basthma\b", r"\bdama\b"],
 "questions": [
  Q("danger", T("Is the person struggling to breathe, unable to speak a full sentence, with blue lips, or chest pain?", "Kya saans lene mein bahut mushkil, poora vaakya nahi bol pa rahe, hoth neele ya seene mein dard hai?", "क्या साँस लेने में बहुत मुश्किल, पूरा वाक्य नहीं बोल पा रहे, होंठ नीले या सीने में दर्द है?"), danger=True),
  Q("blood", T("Coughing up blood, or a known lung/heart condition getting worse?", "Khansi mein khoon ya pehle se phephde/dil ki bimari badh rahi hai?", "खाँसी में खून या पहले से फेफड़ों/दिल की बीमारी बढ़ रही है?")),
  Q("duration", T("How long has the cough lasted?", "Khansi kitne samay se hai?", "खाँसी कितने समय से है?"), [O("short", "Under a week", "Ek hafte se kam", "एक हफ्ते से कम"), O("mid", "1 to 3 weeks", "1 se 3 hafte", "1 से 3 हफ्ते"), O("long", "More than 3 weeks", "3 hafte se zyada", "3 हफ्ते से ज़्यादा")])],
 "rules": [
  R({"danger": DEN}, *EM, T("Severe breathlessness or chest pain is an emergency.", "Bahut saans phoolna ya seene ka dard emergency hai.", "बहुत साँस फूलना या सीने का दर्द इमरजेंसी है।")),
  R({"blood": DEN}, "urgent", "paramedic_home_visit", "same_day", T("Blood in cough or a worsening chronic condition needs same-day examination.", "Khansi mein khoon ya purani bimari badhna aaj hi check maangta hai.", "खाँसी में खून या पुरानी बीमारी बढ़ना आज ही जाँच माँगता है।")),
  R({"duration": ["long"]}, "routine", "teleconsultation", "scheduled", T("A cough over 3 weeks needs a doctor and tests (including TB screening).", "3 hafte se lambi khansi mein doctor aur jaanch (TB screening sahit) zaroori hai.", "3 हफ्ते से लंबी खाँसी में डॉक्टर और जाँच (TB स्क्रीनिंग सहित) ज़रूरी है।")),
  R({"duration": ["mid"]}, "routine", "teleconsultation", "scheduled", T("A cough of 1-3 weeks: book a doctor consult.", "1-3 hafte ki khansi: doctor se consult lein.", "1-3 हफ्ते की खाँसी: डॉक्टर से परामर्श लें।")),
  R({"duration": ["short"]}, "self_care", "teleconsultation", "scheduled", T("A short cough with no warning signs can be managed at home.", "Kam din ki khansi bina warning signs ke ghar par sambhal sakte hain.", "कम दिन की खाँसी बिना चेतावनी संकेत के घर पर संभाली जा सकती है।"),
    T("Warm fluids, rest, avoid smoke and dust (Delhi smog season: stay indoors, mask outdoors). See a doctor if it lasts over a week or breathing worsens.", "Garam paani/kaadha, aaram, dhuen aur dhool se bachein (smog mein ghar ke andar rahein, bahar mask). Ek hafte se zyada ya saans bigde to doctor dikhayen.", "गुनगुना पानी, आराम, धुएँ-धूल से बचें (स्मॉग में घर के अंदर रहें, बाहर मास्क)। एक हफ्ते से ज़्यादा या साँस बिगड़े तो डॉक्टर को दिखाएँ।"))]})

P.append({"id": "vomit_diarrhoea", "title": T("Vomiting or loose motions", "Ulti ya dast", "उल्टी या दस्त"),
 "cues": [r"\bvomit", r"\bulti\b", r"उल्टी", r"\bdiarrh", r"\bloose motion", r"\bdast\b", r"दस्त", r"\bstomach (?:bug|upset)", r"\bfood poison"],
 "questions": [
  Q("danger", T("Is there blood in vomit or stool (or black stool), severe constant belly pain, or is the person very drowsy or hard to wake?", "Kya ulti ya potty mein khoon (ya kala potty), pet mein lagatar tez dard, ya bahut neend/jagana mushkil hai?", "क्या उल्टी या मल में खून (या काला मल), पेट में लगातार तेज़ दर्द, या बहुत नींद/जगाना मुश्किल है?"), danger=True),
  Q("dehydration", T("Very dry mouth, no urine for 8 hours, sunken eyes, or dizziness on standing?", "Munh bahut sookha, 8 ghante se peshab nahi, aankhein dhansi ya khade hone par chakkar?", "मुँह बहुत सूखा, 8 घंटे से पेशाब नहीं, आँखें धँसी या खड़े होने पर चक्कर?")),
  Q("duration", T("For how long?", "Kitne samay se?", "कितने समय से?"), [O("short", "Under 2 days", "2 din se kam", "2 दिन से कम"), O("long", "2 days or more", "2 din ya zyada", "2 दिन या ज़्यादा")])],
 "rules": [
  R({"danger": DEN}, *EM, T("Blood, severe pain or drowsiness is an emergency.", "Khoon, tez dard ya behoshi jaisi neend emergency hai.", "खून, तेज़ दर्द या बेहोशी जैसी नींद इमरजेंसी है।")),
  R({"dehydration": DEN}, "urgent", "paramedic_home_visit", "same_day", T("Possible dehydration needs medical assessment today; a clinician can decide what care is needed.", "Dehydration ke lakshan mein aaj doctor se assessment karwayein; woh sahi care batayenge.", "निर्जलीकरण के लक्षणों की आज डॉक्टर से जाँच करवाएँ; वे सही देखभाल बताएँगे।")),
  R({"duration": ["long"]}, "routine", "teleconsultation", "scheduled", T("Symptoms for 2 days or more: book a doctor consult.", "2 din ya zyada: doctor se consult lein.", "2 दिन या ज़्यादा: डॉक्टर से परामर्श लें।")),
  R({"duration": ["short"]}, "self_care", "teleconsultation", "scheduled", T("Short illness without dehydration can be managed at home.", "Kam din ki bimari bina dehydration ke ghar par sambhal sakte hain.", "कम दिन की बीमारी बिना निर्जलीकरण के घर पर संभाली जा सकती है।"),
    T("Sip ORS or clean fluids often, small light meals, wash hands, no self-started antibiotics. Seek care if you cannot keep fluids down.", "ORS ya saaf paani thoda-thoda baar-baar piyen, halka khana, haath dhoyen, bina doctor ke antibiotic nahi. Paani na tik paye to doctor dikhayen.", "ORS या साफ़ पानी थोड़ा-थोड़ा बार-बार पिएँ, हल्का खाना, हाथ धोएँ, बिना डॉक्टर के एंटीबायोटिक नहीं। पानी न टिके तो डॉक्टर को दिखाएँ।"))]})

P.append({"id": "chest_pain", "title": T("Chest pain", "Seene mein dard", "सीने में दर्द"),
 "cues": [r"\bchest pain\b", r"\bchest (?:tight|pressure|heav)", r"seene (?:me|mein) dard", r"सीने में दर्द", r"सीने में जकड़न", r"\bheart attack\b", r"\bpalpitation"],
 "questions": [
  Q("now", T("Is the pain present now, or did it happen in the last hour?", "Kya dard abhi hai ya pichhle ek ghante mein hua?", "क्या दर्द अभी है या पिछले एक घंटे में हुआ?"), danger=True),
  Q("spread", T("Does it spread to the arm, jaw or back, or come with sweating, breathlessness or nausea?", "Kya dard haath, jabde ya peeth tak jaata hai, ya paseena, saans phoolna, ji machlana hai?", "क्या दर्द हाथ, जबड़े या पीठ तक जाता है, या पसीना, साँस फूलना, जी मचलना है?"), danger=True),
  Q("risk", T("Known heart disease, diabetes or high BP, or age 40 or above?", "Dil ki bimari, sugar ya BP hai, ya umar 40 ya zyada?", "दिल की बीमारी, शुगर या BP है, या उम्र 40 या ज़्यादा?"))],
 "rules": [
  R({"now": DEN}, *EM, T("Chest pain happening now or within the hour is treated as a possible heart attack.", "Abhi ya ek ghante ke andar ka seene ka dard possible heart attack maana jaata hai.", "अभी या एक घंटे के भीतर का सीने का दर्द संभावित हार्ट अटैक माना जाता है।")),
  R({"spread": DEN}, *EM, T("Pain spreading with sweating or breathlessness is a heart-attack warning.", "Dard failna, paseena ya saans phoolna heart attack ki chetavni hai.", "दर्द फैलना, पसीना या साँस फूलना हार्ट अटैक की चेतावनी है।")),
  R({"risk": DEN}, "urgent", "teleconsultation", "same_day", T("Recent chest pain with heart risk factors needs a doctor today (ECG).", "Seene ke dard ke saath dil ke risk factors mein aaj doctor/ECG zaroori hai.", "सीने के दर्द के साथ दिल के जोखिम में आज डॉक्टर/ECG ज़रूरी है।")),
  R({"risk": ["no"]}, "routine", "teleconsultation", "scheduled", T("Pain that has settled, without risk factors: see a doctor soon.", "Dard theek ho chuka aur risk factor nahi: jaldi doctor se milein.", "दर्द ठीक हो चुका और जोखिम नहीं: जल्द डॉक्टर से मिलें।"))]})

P.append({"id": "injury_wound", "title": T("Injury or wound", "Chot ya ghaav", "चोट या घाव"),
 "cues": [r"\binjur", r"\bwound\b", r"\bcut\b", r"\bfell\b", r"\bburn", r"\bbite\b", r"\bchot\b", r"\bghaav\b", r"\bgir gay", r"चोट", r"घाव", r"जल गया", r"\bdressing\b"],
 "questions": [
  Q("danger", T("Heavy bleeding that does not stop after 10 minutes of firm pressure, a bone showing, a head injury with vomiting or drowsiness, or a very large burn?", "10 minute dabane par bhi khoon nahi ruk raha, haddi dikh rahi, sir ki chot ke saath ulti/neend, ya bahut badi jalan?", "10 मिनट दबाने पर भी खून नहीं रुक रहा, हड्डी दिख रही, सिर की चोट के साथ उल्टी/नींद, या बहुत बड़ी जलन?"), danger=True),
  Q("deep", T("Is the wound deep, gaping, dirty, or an animal bite?", "Kya ghaav gehra, khula, gandaa hai ya jaanwar ne kaata hai?", "क्या घाव गहरा, खुला, गंदा है या जानवर ने काटा है?")),
  Q("tetanus", T("Tetanus shot in the last 5 years?", "Pichhle 5 saal mein tetanus injection laga?", "पिछले 5 साल में टिटनेस इंजेक्शन लगा?"))],
 "rules": [
  R({"danger": DEN}, *EM, T("Uncontrolled bleeding, head injury signs or a large burn need emergency care.", "Na rukne wala khoon, sir ki chot ke lakshan ya badi jalan emergency hai.", "न रुकने वाला खून, सिर की चोट के लक्षण या बड़ी जलन इमरजेंसी है।")),
  R({"deep": DEN}, "urgent", "home_nursing", "same_day", T("A deep, dirty or bite wound needs a nurse or doctor today (cleaning, dressing, possible stitches, tetanus/rabies advice).", "Gehre, gande ya kaatne wale ghaav ko aaj nurse/doctor chahiye (safai, dressing, tanke, tetanus/rabies salah).", "गहरे, गंदे या काटने वाले घाव को आज नर्स/डॉक्टर चाहिए (सफ़ाई, ड्रेसिंग, टाँके, टिटनेस/रेबीज़ सलाह)।")),
  R({"tetanus": ["no", "unsure"]}, "routine", "teleconsultation", "scheduled", T("Ask a doctor whether a tetanus booster is needed.", "Doctor se poochhein ki tetanus booster chahiye ya nahi.", "डॉक्टर से पूछें कि टिटनेस बूस्टर चाहिए या नहीं।")),
  R({"tetanus": ["yes"]}, "self_care", "home_nursing", "scheduled", T("A small clean wound can be cared for at home.", "Chhota saaf ghaav ghar par sambhal sakte hain.", "छोटा साफ़ घाव घर पर संभाला जा सकता है।"),
    T("Wash with clean running water, press gently to stop bleeding, cover with a clean dressing, change daily. See a nurse if red, swollen, pus or fever appears.", "Saaf behte paani se dhoyen, halka dabakar khoon rokein, saaf dressing lagayen, roz badlein. Laali, sujan, peep ya bukhar ho to nurse ko dikhayen.", "साफ़ बहते पानी से धोएँ, हल्का दबाकर खून रोकें, साफ़ ड्रेसिंग लगाएँ, रोज़ बदलें। लाली, सूजन, मवाद या बुखार हो तो नर्स को दिखाएँ।"))]})

P.append({"id": "diabetes_bp", "title": T("Diabetes or blood pressure", "Sugar ya BP", "शुगर या बीपी"),
 "cues": [r"\bdiabet", r"\bsugar\b", r"\bblood pressure\b", r"\bbp\b", r"\bhypertension\b", r"\binsulin\b", r"शुगर", r"मधुमेह", r"ब्लड प्रेशर"],
 "questions": [
  Q("danger", T("Confusion, fainting, fruity-smelling breath, or with high BP: severe headache, chest pain, or weakness on one side?", "Uljhan, behoshi, saans mein meethi gandh, ya high BP ke saath tez sir dard, seene mein dard, ek taraf kamzori?", "उलझन, बेहोशी, साँस में मीठी गंध, या हाई BP के साथ तेज़ सिर दर्द, सीने में दर्द, एक तरफ़ कमज़ोरी?"), danger=True),
  Q("reading", T("Is today's reading very high (sugar above 300 mg/dL or BP 180/110 or more) or very low (sugar below 70)?", "Aaj ka reading bahut high (sugar 300 se upar ya BP 180/110 ya zyada) ya bahut low (sugar 70 se neeche) hai?", "आज की रीडिंग बहुत ज़्यादा (शुगर 300 से ऊपर या BP 180/110 या ज़्यादा) या बहुत कम (शुगर 70 से नीचे) है?")),
  Q("need", T("What do you need?", "Aapko kya chahiye?", "आपको क्या चाहिए?"), [O("test", "A routine check or lab test", "Routine check ya lab test", "रूटीन जाँच या लैब टेस्ट"), O("doctor", "Medicine review with a doctor", "Doctor se dawa review", "डॉक्टर से दवा की समीक्षा"), O("other", "Something else", "Kuch aur", "कुछ और")])],
 "rules": [
  R({"danger": DEN}, *EM, T("These are signs of a diabetic or hypertensive emergency.", "Yeh sugar ya BP emergency ke sanket hain.", "ये शुगर या BP इमरजेंसी के संकेत हैं।")),
  R({"reading": DEN}, "urgent", "teleconsultation", "same_day", T("A very high or low reading needs a doctor today.", "Bahut high ya low reading mein aaj doctor chahiye.", "बहुत ज़्यादा या कम रीडिंग में आज डॉक्टर चाहिए।")),
  R({"need": ["test"]}, "routine", "lab_test_home", "scheduled", T("A routine test can be done by home sample collection.", "Routine test ghar par sample collection se ho sakta hai.", "रूटीन टेस्ट घर पर सैंपल कलेक्शन से हो सकता है।")),
  R({"need": ["doctor", "other"]}, "routine", "teleconsultation", "scheduled", T("A medicine review can be done by teleconsultation.", "Dawa review teleconsultation se ho sakta hai.", "दवा की समीक्षा टेली-कंसल्टेशन से हो सकती है।"))]})

P.append({"id": "elderly_weakness", "title": T("Weakness or dizziness", "Kamzori ya chakkar", "कमज़ोरी या चक्कर"),
 "cues": [r"\bweak", r"\bdizz", r"\bkamzori\b", r"\bchakkar\b", r"\bthakan\b", r"कमज़ोरी", r"कमजोरी", r"चक्कर", r"\bfaint", r"\bfatigue\b"],
 "questions": [
  Q("danger", T("Sudden weakness on one side, slurred speech, drooping face, fainting, or a fall with injury?", "Achanak ek taraf kamzori, lada hua bolna, chehra tedha, behoshi ya girne se chot?", "अचानक एक तरफ़ कमज़ोरी, लड़खड़ाती बोली, चेहरा टेढ़ा, बेहोशी या गिरने से चोट?"), danger=True),
  Q("intake", T("Is the person eating, drinking and passing urine normally?", "Kya khana-peena aur peshab normal hai?", "क्या खाना-पीना और पेशाब सामान्य है?")),
  Q("duration", T("How long has this been going on?", "Yeh kitne samay se hai?", "यह कितने समय से है?"), [O("short", "Today or yesterday", "Aaj ya kal se", "आज या कल से"), O("mid", "A few days", "Kuch din se", "कुछ दिन से"), O("long", "Weeks", "Hafton se", "हफ्तों से")])],
 "rules": [
  R({"danger": DEN}, *EM, T("Stroke signs, fainting or injury from a fall are emergencies.", "Stroke ke lakshan, behoshi ya girne ki chot emergency hai.", "स्ट्रोक के लक्षण, बेहोशी या गिरने की चोट इमरजेंसी है।")),
  R({"intake": ["no"]}, "urgent", "paramedic_home_visit", "same_day", T("Not eating, drinking or passing urine needs a same-day check.", "Khana-peena ya peshab band hone par aaj hi check chahiye.", "खाना-पीना या पेशाब बंद होने पर आज ही जाँच चाहिए।")),
  R({"duration": ["mid", "long"]}, "routine", "paramedic_home_visit", "scheduled", T("Ongoing weakness: a home visit for vitals and tests.", "Lagatar kamzori: vitals aur jaanch ke liye home visit.", "लगातार कमज़ोरी: वाइटल्स और जाँच के लिए होम विज़िट।")),
  R({"duration": ["short"]}, "self_care", "paramedic_home_visit", "scheduled", T("New mild weakness with normal intake can be watched at home for a day.", "Nayi halki kamzori, khana-peena normal: ek din ghar par dekh sakte hain.", "नई हल्की कमज़ोरी, खाना-पीना सामान्य: एक दिन घर पर देख सकते हैं।"),
    T("Rest, fluids, a light meal, stand up slowly. Book a visit if it lasts beyond a day or worsens.", "Aaram, paani, halka khana, dheere uthein. Ek din se zyada ya badhe to visit book karein.", "आराम, पानी, हल्का खाना, धीरे उठें। एक दिन से ज़्यादा या बढ़े तो विज़िट बुक करें।"))]})

DOC = {"status": "UNREVIEWED (demo): drafted from public, general guidance (WHO IMCI-style danger signs, NHS 111-style pathway structure, MoHFW dengue warning signs). Not clinician-reviewed. Thresholds such as sugar 300/70 and BP 180/110 must be checked by a clinician.",
 "dispositions": {"emergency": "care_type emergency_112, urgency emergency", "urgent": "urgency same_day", "routine": "urgency scheduled", "self_care": "urgency scheduled, plus `advice`; the care type stays bookable"},
 "strictness": {"age_groups": {"infant": {"max_years": 1}, "child": {"max_years": 5}, "elder": {"min_years": 65}},
   "raise": {"infant": {"self_care": "urgent", "routine": "urgent"}, "child": {"self_care": "routine"}, "pregnant": {"self_care": "urgent", "routine": "urgent"}, "elder": {"self_care": "routine"}},
   "note": "Infants and pregnant women never get self-care or routine from these pathways; they are raised to a same-day review. Children under 5 and over-65s never get self-care."},
 "unknown_policy": "Unknown danger signs require same-day human assessment; only affirmative danger answers trigger emergency rules.",
 "max_questions": 4, "pathways": P}
for pathway in P:
    for rule in pathway["rules"]:
        if rule["disposition"] == "emergency":
            rule["when"] = {key: [v for v in values if v != "unsure"] for key, values in rule["when"].items()}
OUT.write_text(json.dumps(DOC, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(P), "pathways ->", OUT)
