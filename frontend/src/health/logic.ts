import type { HealthState, Reading } from './types.ts';
export function validateReading(reading: Pick<Reading, 'metric' | 'value' | 'secondary'>): boolean {
  if (!Number.isFinite(reading.value) || reading.value <= 0) return false;
  if (reading.metric === 'Blood pressure' && (!Number.isFinite(reading.secondary) || reading.secondary! <= 0 || reading.value <= reading.secondary!)) return false;
  if (reading.metric === 'SpO2' && reading.value > 100) return false;
  return true;
}
export function logDose(state: HealthState, medicationId: string, date: string, action: 'Taken' | 'Skipped', time: string): HealthState {
  const medication = state.medications.find(m => m.id === medicationId);
  if (!medication) return state;
  return { ...state, doses: [...state.doses.filter(d => !(d.medicationId === medicationId && d.date === date)), { id: `${medicationId}_${date}`, medicationId, date, action, time }] };
}
export function downloadText(name: string, content: string, type = 'text/plain;charset=utf-8') {
  const url = URL.createObjectURL(new Blob([content], { type })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
