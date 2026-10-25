import assert from 'node:assert/strict';
import { test } from 'node:test';
import { buildPatientContext } from '../src/health/context.ts';
import { initialHealthState } from '../src/health/data.ts';

test('a saved member is sent as the active patient', () => {
  const state = { ...initialHealthState(), activeId: 'P_02' };
  const ctx = buildPatientContext(state)!;
  assert.equal(ctx.active_member_id, 'P_02');
  assert.ok(ctx.members.length >= 2);
});

test('"Someone else" sends no saved member data and no active patient', () => {
  const ctx = buildPatientContext({ ...initialHealthState(), careForOther: true })!;
  assert.deepEqual(ctx, { active_member_id: null, members: [] });
});

test('turning profile sharing off sends nothing, even for a saved member', () => {
  assert.equal(buildPatientContext({ ...initialHealthState(), shareProfile: false }), undefined);
  assert.equal(buildPatientContext({ ...initialHealthState(), shareProfile: false, careForOther: true }), undefined);
});
