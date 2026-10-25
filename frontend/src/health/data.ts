import { localDate } from '../lib/flow.ts';
import type { HealthState, Hospital, Metric, RecordCategory } from './types';
export const categories: RecordCategory[] = ['Lab report', 'Prescription', 'Radiology', 'Cardiology', 'Vaccination', 'Consultation'];
export const categoryHi: Record<RecordCategory, string> = { 'Lab report': 'लैब रिपोर्ट', Prescription: 'प्रिस्क्रिप्शन', Radiology: 'रेडियोलॉजी', Cardiology: 'कार्डियोलॉजी', Vaccination: 'टीकाकरण', Consultation: 'परामर्श' };
export const metrics: Metric[] = ['Blood pressure', 'Blood glucose', 'Heart rate', 'Weight', 'SpO2'];
export const metricInfo: Record<Metric, { unit: string; hi: string }> = { 'Blood pressure': { unit: 'mmHg', hi: 'रक्तचाप' }, 'Blood glucose': { unit: 'mg/dL', hi: 'ब्लड ग्लूकोज़' }, 'Heart rate': { unit: 'bpm', hi: 'हृदय गति' }, Weight: { unit: 'kg', hi: 'वज़न' }, SpO2: { unit: '%', hi: 'SpO2' } };
export const hospitals: Hospital[] = [
  { id: 'H_01', name: 'Compass Community Clinic', area: 'Okhla · Fictional provider', services: ['General consultation', 'Nursing', 'Lab collection'] },
  { id: 'H_02', name: 'Greenway Family Hospital', area: 'Saket · Fictional provider', services: ['General medicine', 'Specialist consultation', 'Diagnostics'] },
];
export function initialHealthState(): HealthState {
  const records = [
    { id: `R_0_1`, title: 'Routine health panel', category: 'Lab report' as const, date: localDate(-3), source: 'Compass Demo Diagnostics', status: 'Sample reviewed' as const, description: 'Synthetic laboratory document. Includes sample blood-count and glucose fields for demonstrating record organization. No clinical interpretation has been performed.', tags: ['Routine check-up', 'Blood test'] },
    { id: `R_0_2`, title: 'Follow-up consultation', category: 'Consultation' as const, date: localDate(-9), source: 'Compass Demo Clinic', status: 'Sample reviewed' as const, description: 'Synthetic visit note. A follow-up was discussed in this made-up scenario. This is not a prescription or medical advice.', tags: ['Follow-up', 'General care'] },
    { id: `R_0_3`, title: 'Sample medication record', category: 'Prescription' as const, date: localDate(-9), source: 'Compass Demo Clinic', status: 'Sample reviewed' as const, description: 'Fictional medication schedule for UI testing only. No real medicine or dosage is prescribed.', tags: ['Medication schedule'] },
  ];
  const readings = Array.from({ length: 6 }, (_, i) => [
    { id: `BP_0_${i}`, metric: 'Blood pressure' as const, value: [126, 123, 128, 122, 124, 121][i], secondary: [82, 80, 84, 80, 81, 79][i], date: localDate(-5 + i), time: '08:00', note: 'Synthetic reading' },
    { id: `BG_0_${i}`, metric: 'Blood glucose' as const, value: [102, 108, 104, 106, 99, 103][i], date: localDate(-5 + i), time: '08:00', note: 'Synthetic reading; context not assessed' },
    { id: `HR_0_${i}`, metric: 'Heart rate' as const, value: [74, 76, 72, 75, 73, 72][i], date: localDate(-5 + i), time: '08:00', note: 'Synthetic reading' },
  ]).flat();
  return {
    records, readings,
    medications: [{ id: `M_0`, name: 'Demo medicine A', instructions: 'Sample reminder only. Follow the prescriber’s actual directions.', time: '20:00', startDate: localDate(-3), endDate: localDate(10), active: true }],
    doses: [], chats: [], grants: [], linkedHospitals: [], tokens: [], careMessages: [],
    notices: [{ id: 'N_1', title: 'Your sample records are ready', body: 'Open the briefcase to explore records grouped by type and date.', read: false, page: 'records' }],
  };
}
