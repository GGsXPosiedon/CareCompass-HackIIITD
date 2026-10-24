import assert from 'node:assert/strict';
import { test } from 'node:test';
import { availableSlots, nextView } from '../src/lib/flow.ts';
import { validateCaregivers, validateTriage } from '../src/lib/contracts.ts';
import { mockIntake } from '../src/lib/mock.ts';
import { caregivers } from '../src/data.ts';
import type { IntakeRequest, Message, TriageResponse } from '../src/types.ts';

const baseline: TriageResponse = { follow_up_question: null, care_type: 'paramedic_home_visit', urgency: 'same_day', red_flags: [], reasoning: 'Synthetic test', matched_caregivers: [{ caregiver_id: 'CG_014', score: .9, reason: 'Synthetic match' }] };
const request = (text: string, history: Message[] = [], language: IntakeRequest['language'] = 'en'): IntakeRequest => ({ user_input: text, language, location: { lat: 28.54, lng: 77.27 }, conversation_history: history });

test('red flags override a follow-up and existing caregiver matches', () => {
  const output = validateTriage({ ...baseline, follow_up_question: 'One more question?', red_flags: ['Emergency signal'] });
  assert.equal(nextView(output), 'emergency'); assert.equal(output.follow_up_question, null); assert.deepEqual(output.matched_caregivers, []);
});
test('sparse emergency response still escalates instead of failing validation', () => {
  assert.equal(nextView(validateTriage({ urgency: 'immediate' })), 'emergency');
  assert.equal(nextView(validateTriage({ care_type: 'emergency_referral', matched_caregivers: 'invalid' })), 'emergency');
});
test('malformed non-emergency responses cannot display a recommendation', () => {
  for (const value of [null, {}, { ...baseline, care_type: 'unknown' }, { ...baseline, care_type: null }, { ...baseline, urgency: null }, { ...baseline, red_flags: 'none' }, { ...baseline, follow_up_question: '' }]) assert.throws(() => validateTriage(value));
});
test('invalid and duplicate ranking records are rejected', () => {
  for (const matched_caregivers of [[{ caregiver_id: 'x', score: NaN, reason: 'x' }], [{ caregiver_id: 'x', score: 1.2, reason: 'x' }], [baseline.matched_caregivers[0], baseline.matched_caregivers[0]]]) assert.throws(() => validateTriage({ ...baseline, matched_caregivers }));
});
test('follow-up takes precedence over normal recommendation', () => {
  assert.equal(nextView(validateTriage({ ...baseline, care_type: null, urgency: null, follow_up_question: 'Age?' })), 'questions');
});
test('demo asks two questions and returns the fever fixture', () => {
  const first = mockIntake(request('Papa ko bukhar aur khansi hai'));
  assert.ok(first.follow_up_question);
  const history: Message[] = [{ role: 'user', content: 'Papa ko bukhar aur khansi hai' }, { role: 'assistant', content: first.follow_up_question! }];
  const second = mockIntake(request('60 years or older', history));
  history.push({ role: 'user', content: '60 years or older' }, { role: 'assistant', content: second.follow_up_question! });
  const final = mockIntake(request('No', history));
  assert.equal(final.follow_up_question, null); assert.equal(final.care_type, 'paramedic_home_visit'); assert.equal(final.urgency, 'same_day'); assert.equal(final.matched_caregivers.length, 3);
});
test('affirmative or uncertain emergency follow-up bypasses matching', () => {
  const history: Message[] = [{ role: 'user', content: 'fever' }, { role: 'assistant', content: 'Age?' }, { role: 'user', content: '60' }, { role: 'assistant', content: 'Is there any difficulty breathing or severe chest pain right now?' }];
  for (const input of ['Yes', 'Not sure']) { const result = mockIntake(request(input, history)); assert.equal(nextView(result), 'emergency'); assert.deepEqual(result.matched_caregivers, []); }
});
test('Hindi affirmative follow-up immediately escalates', () => {
  const history: Message[] = [{ role: 'assistant', content: 'क्या साँस लेने में कठिनाई है?' }];
  assert.equal(nextView(mockIntake(request('हाँ', history, 'hi'))), 'emergency');
});
test('English, Hindi and Hinglish emergency fixtures escalate on first input', () => {
  for (const input of ['My father cannot breathe', 'Papa ko saans nahi aa rahi', 'पापा को साँस नहीं आ रही है']) assert.equal(nextView(mockIntake(request(input))), 'emergency');
});
test('outside-coverage demo preserves care urgency while returning no matches', () => {
  const r = request('fever', [{ role: 'assistant', content: 'Age?' }, { role: 'assistant', content: 'Breathing?' }]);
  r.location = { lat: 0, lng: 0 };
  const result = mockIntake(r); assert.equal(result.urgency, 'same_day'); assert.deepEqual(result.matched_caregivers, []);
});
test('invalid caregiver data cannot reach booking controls', () => {
  assert.equal(validateCaregivers(caregivers).length, caregivers.length);
  for (const value of [[{ ...caregivers[0], slots: ['25:99'] }], [{ ...caregivers[0], languages: undefined }], [{ ...caregivers[0], rating: 9 }], [caregivers[0], caregivers[0]]]) assert.throws(() => validateCaregivers(value));
});
test('past slots are excluded and future dates retain their times', () => {
  const now = new Date('2026-10-24T13:00:00');
  assert.deepEqual(availableSlots(['10:00', '13:00', '14:00'], '2026-10-24', now), ['14:00']);
  assert.deepEqual(availableSlots(['10:00', '14:00'], '2026-10-25', now), ['10:00', '14:00']);
});
