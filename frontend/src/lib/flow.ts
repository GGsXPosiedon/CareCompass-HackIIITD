import type { TriageResponse } from '../types.ts';
export function isEmergency(response: TriageResponse): boolean {
  return response.red_flags.length > 0 || response.urgency === 'emergency' || response.care_type === 'emergency_112';
}
export function nextView(response: TriageResponse): 'emergency' | 'questions' | 'recommendation' {
  if (isEmergency(response)) return 'emergency';
  return response.follow_up_question ? 'questions' : 'recommendation';
}
export function localDate(offset = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + offset);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}
export function formatDate(date: string, hindi = false): string {
  return new Intl.DateTimeFormat(hindi ? 'hi-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(`${date}T12:00:00`));
}
export function formatTime(time: string, hindi = false): string {
  return new Intl.DateTimeFormat(hindi ? 'hi-IN' : 'en-IN', { hour: 'numeric', minute: '2-digit' }).format(new Date(`2000-01-01T${time}:00`));
}
export function availableSlots(slots: string[], date: string, now = new Date()): string[] {
  return slots.filter(slot => new Date(`${date}T${slot}:00`).getTime() > now.getTime());
}
