import assert from 'node:assert/strict';
import { test } from 'node:test';
import { validateCaregivers } from '../src/lib/contracts.ts';

test('backend caregiver profile without distance or reviews is accepted', () => {
  const profile = { id: 'SYN_001', name: 'Asha', initials: 'A', role: 'Medic', roleHi: 'मेडिक', careType: 'home_nursing', experience: 8, distance: null, languages: ['Hindi'], rating: 4.8, skills: ['injection im'], skillsHi: ['x'], slots: ['10:00'], tint: 'sage' };
  assert.equal(validateCaregivers([profile]).length, 1);
  assert.throws(() => validateCaregivers([{ ...profile, careType: 'emergency_112' }]));
  assert.throws(() => validateCaregivers([{ ...profile, careType: 'gp_teleconsult' }]));
});
