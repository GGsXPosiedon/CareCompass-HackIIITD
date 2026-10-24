import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildPatientContext } from '../src/health/context.ts';
import { initialHealthState } from '../src/health/data.ts';
import { validateCaregivers } from '../src/lib/contracts.ts';

test('patient context carries saved profile data per member and respects sharing off', () => {
  const state = initialHealthState();
  const ctx = buildPatientContext(state)!;
  assert.equal(ctx.members.length, state.members.length);
  assert.equal(ctx.active_member_id, state.activeId);
  const father = ctx.members.find(m => m.relation === 'Father')!;
  assert.ok(father.conditions.length && father.allergies.length && father.medications.length && father.notes.length);
  assert.ok(father.notes.length <= 10);
  assert.equal(buildPatientContext({ ...state, shareProfile: false }), undefined);
});
test('patient context trims over-long text', () => {
  const state = initialHealthState();
  state.members[0].conditions = ['x'.repeat(500)];
  assert.ok(buildPatientContext(state)!.members[0].conditions[0].length <= 80);
});
test('backend caregiver profile without distance or reviews is accepted', () => {
  const profile = { id: 'SYN_001', name: 'Asha', initials: 'A', role: 'Medic', roleHi: 'मेडिक', careType: 'home_nursing', experience: 8, distance: null, languages: ['Hindi'], rating: 4.8, skills: ['injection im'], skillsHi: ['x'], slots: ['10:00'], tint: 'sage' };
  assert.equal(validateCaregivers([profile]).length, 1);
  assert.throws(() => validateCaregivers([{ ...profile, careType: 'emergency_112' }]));
  assert.throws(() => validateCaregivers([{ ...profile, careType: 'gp_teleconsult' }]));
});
