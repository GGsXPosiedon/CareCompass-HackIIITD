import assert from 'node:assert/strict';
import { test } from 'node:test';
import { initialHealthState } from '../src/health/data.ts';
import { logDose, validateReading } from '../src/health/logic.ts';

test('Briefcase has one collection with no saved patient identity or profile defaults', () => {
  const state = initialHealthState();
  for (const key of ['members', 'activeId', 'shareProfile', 'careForOther']) assert.ok(!(key in state));
  assert.equal(state.records.length, 3);
  for (const item of [...state.records, ...state.readings, ...state.medications]) assert.ok(!('memberId' in item));
});

test('dose logging replaces the same medication/day entry without duplicate logs', () => {
  let state = logDose(initialHealthState(), 'M_0', '2026-10-24', 'Taken', '08:00');
  state = logDose(state, 'M_0', '2026-10-24', 'Skipped', '08:01');
  assert.equal(state.doses.length, 1);
  assert.equal(state.doses[0].action, 'Skipped');
  assert.equal(logDose(state, 'missing', '2026-10-24', 'Taken', '08:00'), state);
});

test('reading validation rejects non-numeric, impossible percentage and reversed pressure entries', () => {
  assert.equal(validateReading({ metric: 'SpO2', value: 101 }), false);
  assert.equal(validateReading({ metric: 'Weight', value: NaN }), false);
  assert.equal(validateReading({ metric: 'Blood glucose', value: 0 }), false);
  assert.equal(validateReading({ metric: 'Blood pressure', value: 80, secondary: 120 }), false);
  assert.equal(validateReading({ metric: 'Blood pressure', value: 120, secondary: 80 }), true);
});

test('fresh Briefcase state does not retain uploaded records or requests', () => {
  const state = initialHealthState();
  state.records.push({ ...state.records[0], id: 'upload' });
  state.careMessages.push({ id: 'msg', text: 'Synthetic attachment' });
  const clean = initialHealthState();
  assert.equal(clean.records.length, 3);
  assert.deepEqual(clean.careMessages, []);
  assert.deepEqual(clean.tokens, []);
});
