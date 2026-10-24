import type { Caregiver, TriageResponse } from '../types.ts';

const careTypes = new Set(['paramedic_home_visit', 'nurse_home_visit', 'gp_teleconsult', 'specialist_consult', 'emergency_referral']);
const urgencies = new Set(['routine', 'same_day', 'immediate']);

export function validateTriage(value: unknown): TriageResponse {
  if (!value || typeof value !== 'object') throw new Error('INVALID_RESPONSE');
  const r = value as Record<string, unknown>;
  // Escalation must not be blocked by incomplete or conflicting non-emergency fields.
  const flags = Array.isArray(r.red_flags) ? r.red_flags.filter((flag): flag is string => typeof flag === 'string') : [];
  if (flags.length || r.urgency === 'immediate' || r.care_type === 'emergency_referral') {
    return { follow_up_question: null, care_type: 'emergency_referral', urgency: 'immediate', red_flags: flags, reasoning: typeof r.reasoning === 'string' ? r.reasoning : '', matched_caregivers: [] };
  }
  if (!(r.follow_up_question === null || (typeof r.follow_up_question === 'string' && r.follow_up_question.trim())) || !Array.isArray(r.red_flags) || !r.red_flags.every(f => typeof f === 'string') || typeof r.reasoning !== 'string' || !Array.isArray(r.matched_caregivers)) throw new Error('INVALID_RESPONSE');
  if (!(r.care_type === null || careTypes.has(String(r.care_type))) || !(r.urgency === null || urgencies.has(String(r.urgency)))) throw new Error('INVALID_RESPONSE');
  if (!r.follow_up_question && (!r.care_type || !r.urgency)) throw new Error('INVALID_RESPONSE');
  const seen = new Set<string>();
  for (const m of r.matched_caregivers) {
    if (!m || typeof m.caregiver_id !== 'string' || !m.caregiver_id || seen.has(m.caregiver_id) || typeof m.score !== 'number' || !Number.isFinite(m.score) || m.score < 0 || m.score > 1 || typeof m.reason !== 'string') throw new Error('INVALID_RESPONSE');
    seen.add(m.caregiver_id);
  }
  if (r.answer_options !== undefined && (!Array.isArray(r.answer_options) || !r.answer_options.every(a => typeof a === 'string'))) throw new Error('INVALID_RESPONSE');
  return value as TriageResponse;
}

export function validateCaregivers(value: unknown): Caregiver[] {
  if (!Array.isArray(value)) throw new Error('INVALID_PROFILES');
  const ids = new Set<string>();
  for (const item of value) {
    if (!item || typeof item !== 'object') throw new Error('INVALID_PROFILES');
    const c = item as Record<string, unknown>;
    for (const key of ['id', 'name', 'initials', 'role', 'roleHi', 'careType', 'tint']) if (typeof c[key] !== 'string' || !c[key]) throw new Error('INVALID_PROFILES');
    if (!careTypes.has(String(c.careType)) || c.careType === 'emergency_referral' || ids.has(String(c.id))) throw new Error('INVALID_PROFILES');
    for (const key of ['experience', 'distance', 'rating', 'reviews']) if (typeof c[key] !== 'number' || !Number.isFinite(c[key]) || (c[key] as number) < 0) throw new Error('INVALID_PROFILES');
    if ((c.rating as number) > 5) throw new Error('INVALID_PROFILES');
    for (const key of ['languages', 'skills', 'skillsHi', 'slots']) if (!Array.isArray(c[key]) || !(c[key] as unknown[]).every(item => typeof item === 'string')) throw new Error('INVALID_PROFILES');
    if (!(c.slots as string[]).every(slot => /^([01]\d|2[0-3]):[0-5]\d$/.test(slot))) throw new Error('INVALID_PROFILES');
    ids.add(String(c.id));
  }
  return value as Caregiver[];
}
