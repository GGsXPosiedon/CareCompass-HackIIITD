import type { PatientContext } from '../types.ts';
import type { HealthState } from './types.ts';

const clip = (value: string, max: number) => value.replace(/\s+/g, ' ').trim().slice(0, max);

// What the assistant may know about the family: only what the user has saved in their Profile/Briefcase.
// Sent per request (the API is stateless). Returns undefined when the user turned sharing off.
export function buildPatientContext(state: HealthState): PatientContext | undefined {
  if (state.shareProfile === false) return undefined;
  const members = state.members.slice(0, 12).map(m => {
    const meds = state.medications.filter(x => x.memberId === m.id && x.active).slice(0, 10).map(x => ({ name: clip(x.name, 80) }));
    const records = [...state.records].filter(r => r.memberId === m.id).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4)
      .map(r => clip(`${r.date}: ${r.category} - ${r.title}`, 120));
    const latest = new Map<string, string>();
    [...state.readings].filter(r => r.memberId === m.id).sort((a, b) => a.date.localeCompare(b.date)).forEach(r => {
      latest.set(r.metric, `${r.metric} ${r.value}${r.secondary ? `/${r.secondary}` : ''} on ${r.date}`);
    });
    return {
      id: m.id, name: clip(m.name, 60), relation: clip(m.relation, 30), age: m.age, ...(m.sex ? { sex: clip(m.sex, 20) } : {}),
      conditions: (m.conditions ?? []).slice(0, 20).map(c => clip(c, 80)).filter(Boolean),
      allergies: m.allergies.slice(0, 20).map(a => clip(a, 80)).filter(Boolean),
      medications: meds,
      notes: [...records, ...latest.values()].slice(0, 10),
    };
  });
  return { active_member_id: state.activeId, members };
}
