import { caregivers } from '../data.ts';
import type { CareType, IntakeRequest, TriageResponse } from '../types.ts';

// Scripted synthetic fixtures for demonstrating UI states only. This is NOT clinical triage.
export function mockIntake(request: IntakeRequest): TriageResponse {
  const hi = request.language === 'hi';
  const userMessages = [...request.conversation_history.filter(m => m.role === 'user').map(m => m.content), request.user_input];
  const text = userMessages.join(' ').toLowerCase();
  const response: TriageResponse = { follow_up_question: null, care_type: null, urgency: null, red_flags: [], reasoning: '', matched_caregivers: [] };
  // An affirmative follow-up is used only for the demo's explicit emergency question.
  const question = [...request.conversation_history].reverse().find(m => m.role === 'assistant')?.content ?? '';
  const redQuestion = /breathing|साँस/.test(question);
  const affirmative = /^(yes|haan|han|हाँ|हां|जी)(\b|\s|[।.!]|$)/i.test(request.user_input.trim());
  const emergency = /emergency demo|cannot breathe|can't breathe|severe chest pain|unconscious|behosh|saans nahi|साँस नहीं|बेहोश|आपातकाल का डेमो/.test(text) || (redQuestion && affirmative);
  if (emergency) return { ...response, care_type: 'emergency_112', urgency: 'emergency', red_flags: [hi ? 'डेमो में आपातकाल का संकेत' : 'Emergency signal in this demo'], reasoning: hi ? 'इस नमूने में तत्काल मदद का रास्ता दिखाया जाता है। देखभालकर्ता की बुकिंग छोड़ दी गई है।' : 'This sample demonstrates immediate escalation. Caregiver matching and booking have been bypassed.' };
  const answers = request.conversation_history.filter(m => m.role === 'assistant').length;
  if (answers === 0) return { ...response, follow_up_question: hi ? 'जिस व्यक्ति को देखभाल चाहिए, उसकी उम्र कितनी है?' : 'How old is the person who needs care?', answer_options: hi ? ['18 वर्ष से कम', '18–59 वर्ष', '60 वर्ष या अधिक'] : ['Under 18', '18–59 years', '60 years or older'] };
  if (answers === 1) return { ...response, follow_up_question: hi ? 'क्या अभी साँस लेने में कठिनाई या सीने में तेज़ दर्द है?' : 'Is there any difficulty breathing or severe chest pain right now?', answer_options: hi ? ['नहीं', 'हाँ', 'पता नहीं'] : ['No', 'Yes', 'Not sure'] };
  if (redQuestion && /not sure|idk|pata nahi|पता नहीं/.test(request.user_input.toLowerCase())) return { ...response, care_type: 'teleconsultation', urgency: 'same_day', reasoning: hi ? 'पता न हो तो कोई बात नहीं। आज डॉक्टर से बात करके जाँच करवाएँ। साँस में तकलीफ़, सीने में दर्द या बेहोशी हो तो तुरंत 112 पर कॉल करें।' : "It's okay if you're not sure. Speak to a doctor today for assessment. If breathing difficulty, chest pain or collapse occurs, call 112 immediately." };
  let careType: CareType = 'teleconsultation';
  if (/fever|cough|bukhar|khansi|बुखार|खाँसी/.test(text)) careType = 'paramedic_home_visit';
  if (/dress|wound|nurse|ड्रेसिंग|घाव|नर्स/.test(text)) careType = 'home_nursing';
  if (/blood test|lab test|sample|खून की जाँच|ब्लड टेस्ट/.test(text)) careType = 'lab_test_home';
  const sameDay = careType !== 'lab_test_home';
  const matched = request.location.lat === 0 ? [] : caregivers.filter(c => c.careType === careType).map((c, i) => ({ caregiver_id: c.id, score: Number((0.94 - i * 0.06).toFixed(2)), reason: hi ? `इस नमूने में उपयुक्त कौशल, हिंदी भाषा और ${c.distance === 0 ? 'ऑनलाइन परामर्श' : `${c.distance} किमी की दूरी`}।` : `Relevant skills, Hindi-speaking, ${c.distance === 0 ? 'available online' : `${c.distance} km from the demo location`}.` }));
  return { ...response, care_type: careType, urgency: sameDay ? 'same_day' : 'scheduled', reasoning: hi ? 'चुने गए कृत्रिम उदाहरण के लिए यह पहले से तय डेमो परिणाम है। यह चिकित्सीय मूल्यांकन नहीं है।' : 'A preset outcome for this synthetic example, used to demonstrate the care journey. This is not a clinical assessment.', matched_caregivers: matched };
}
