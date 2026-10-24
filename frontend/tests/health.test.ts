import assert from 'node:assert/strict';
import { test } from 'node:test';
import { initialHealthState } from '../src/health/data.ts';
import { logDose, profileData, sampleReply, validateReading } from '../src/health/logic.ts';

test('family profiles isolate records, readings, conversations and consent history', () => {
  const state = initialHealthState();
  state.records.push({...state.records[0],id:'private-sample',memberId:'P_02'});
  const first = profileData(state,'P_01'); const second = profileData(state,'P_02');
  assert.equal(first.records.length,3); assert.equal(second.records.length,4);
  assert.ok(first.records.every(r=>r.memberId==='P_01'));
  assert.ok(first.readings.every(r=>r.memberId==='P_01'));
  assert.equal(first.readings.length,18);
});
test('record summaries and assistant answers use the selected family profile', () => {
  const state=initialHealthState();state.records.push({...state.records[0],id:'extra',memberId:'P_02'});
  assert.match(sampleReply('What is in my briefcase?',state,'P_01',false),/3 sample records/);
  assert.match(sampleReply('What is in my briefcase?',state,'P_02',false),/4 sample records/);
  assert.match(sampleReply('मेरी रिपोर्ट',state,'P_02',true),/4 नमूना रिकॉर्ड/);
});
test('dose logging is idempotent for a medication and day, and keeps other profiles separate', () => {
  let state=initialHealthState();state=logDose(state,'M_0','2026-10-24','Taken','08:00');
  state=logDose(state,'M_0','2026-10-24','Taken','08:01');assert.equal(state.doses.length,1);
  state=logDose(state,'M_0','2026-10-24','Skipped','08:02');assert.equal(state.doses[0].action,'Skipped');
  state=logDose(state,'M_1','2026-10-24','Taken','08:00');assert.equal(state.doses.length,2);assert.equal(state.doses[1].memberId,'P_02');
});
test('reading validation rejects non-numeric, impossible percentage and reversed pressure entries', () => {
  assert.equal(validateReading({metric:'SpO2',value:101}),false);
  assert.equal(validateReading({metric:'Weight',value:NaN}),false);
  assert.equal(validateReading({metric:'Blood glucose',value:0}),false);
  assert.equal(validateReading({metric:'Blood pressure',value:80,secondary:120}),false);
  assert.equal(validateReading({metric:'Blood pressure',value:120,secondary:80}),true);
});
test('demo assistant does not prescribe or claim to be live clinical AI', () => {
  const state=initialHealthState();
  assert.match(sampleReply('What medicine should I take?',state,'P_01',false),/does not recommend medicines or doses/);
  assert.match(sampleReply('Diagnose my symptoms',state,'P_01',false),/scripted demo assistant/);
});
test('reset factories do not retain uploaded records, messages, or linked identities', () => {
  const state=initialHealthState();state.careMessages.push({id:'msg',memberId:'P_01',text:'Synthetic attachment'});state.abhaLinked.push('P_01');
  const clean=initialHealthState();assert.deepEqual(clean.careMessages,[]);assert.deepEqual(clean.abhaLinked,[]);assert.equal(clean.records.length,9);
});
