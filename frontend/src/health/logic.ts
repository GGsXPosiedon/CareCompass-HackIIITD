import type { HealthState, Reading } from './types.ts';
export function profileData(state: HealthState, id: string) {
  return { records: state.records.filter(r => r.memberId === id), readings: state.readings.filter(r => r.memberId === id), medications: state.medications.filter(m => m.memberId === id), chats: state.chats.filter(c => c.memberId === id), grants: state.grants.filter(g => g.memberId === id), tokens: state.tokens.filter(t => t.memberId === id) };
}
export function validateReading(reading: Pick<Reading, 'metric' | 'value' | 'secondary'>): boolean {
  if (!Number.isFinite(reading.value) || reading.value <= 0) return false;
  if (reading.metric === 'Blood pressure' && (!Number.isFinite(reading.secondary) || reading.secondary! <= 0 || reading.value <= reading.secondary!)) return false;
  if (reading.metric === 'SpO2' && reading.value > 100) return false;
  return true;
}
export function logDose(state: HealthState, medicationId: string, date: string, action: 'Taken' | 'Skipped', time: string): HealthState {
  const medication = state.medications.find(m => m.id === medicationId);
  if (!medication) return state;
  return { ...state, doses: [...state.doses.filter(d => !(d.medicationId === medicationId && d.date === date)), { id: `${medicationId}_${date}`, medicationId, memberId: medication.memberId, date, action, time }] };
}
export function sampleReply(question: string, state: HealthState, memberId: string, hi: boolean): string {
  const data = profileData(state, memberId);
  if (/dose|medicine|medication|दवा|खुराक/i.test(question)) return hi ? `इस प्रोफ़ाइल में ${data.medications.filter(m => m.active).length} सक्रिय नमूना रिमाइंडर हैं। समय देखने या बदलने के लिए दवाएँ खोलें। यह डेमो खुराक या दवा का सुझाव नहीं देता।` : `This profile has ${data.medications.filter(m => m.active).length} active sample reminder(s). Open Medications to view or edit their times. This demo does not recommend medicines or doses.`;
  if (/blood|sugar|glucose|pressure|reading|शुगर|रक्त|रीडिंग/i.test(question)) return hi ? `इस प्रोफ़ाइल में ${data.readings.length} कृत्रिम रीडिंग हैं। वाइटल्स में तारीख़ के अनुसार देखें। ये माप चिकित्सीय रूप से समझाए नहीं गए हैं।` : `There are ${data.readings.length} synthetic readings for this profile. Open Vitals to compare them by date. These measurements have not been clinically interpreted.`;
  if (/briefcase|share|record|report|summary|ब्रीफ़केस|इतिहास|रिपोर्ट|सारांश/i.test(question)) return hi ? `इस प्रोफ़ाइल में ${data.records.length} नमूना रिकॉर्ड हैं। ब्रीफ़केस में रिकॉर्ड खोलें, सारांश देखें या डेमो एक्सेस पैकेज बनाएँ। कोई फ़ाइल बाहर नहीं भेजी जाती।` : `This profile has ${data.records.length} sample records. Open Briefcase to view a document, review the summary or create a demo access package. No files are sent to another person.`;
  return hi ? 'यह एक पहले से तय डेमो सहायक है, लाइव चिकित्सीय AI नहीं। आप नमूना रिकॉर्ड, रीडिंग, रिमाइंडर या देखभाल का रास्ता पूछ सकते हैं। लक्षणों के लिए “देखभाल खोजें” खोलें।' : 'This is a scripted demo assistant, not live medical AI. Ask about the sample records, readings, reminders or care journey. For symptom navigation, open Find care. No diagnosis or treatment is provided.';
}
export function downloadText(name: string, content: string, type = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([content], { type })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
