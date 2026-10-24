import assert from 'node:assert/strict';
import { test } from 'node:test';
import { HISTORY_KEY, readHistory, recentConversations, requestHistory, saveConversation } from '../src/lib/history.ts';
import type { CareConversation } from '../src/lib/history.ts';
import type { Message } from '../src/types.ts';

const entry: CareConversation = {
  id: 'one', title: 'Original request', input: 'Original request', person: 'me', language: 'en',
  location: { lat: 28.54, lng: 77.27, label: 'Delhi' }, updatedAt: '2026-10-24T12:00:00Z',
  messages: [{ role: 'user', content: 'Original request' }, { role: 'assistant', content: 'What care?', kind: 'follow_up' }],
  result: { follow_up_question: 'What care?', care_type: null, urgency: null, red_flags: [], reasoning: '', matched_caregivers: [] },
};
test('sidebar recents show only the latest five without removing older chat history', () => {
  const history = Array.from({ length: 9 }, (_, i) => ({ ...entry, id: String(i), updatedAt: new Date(2026, 9, 20 + i).toISOString() }));
  assert.deepEqual(recentConversations(history).map(item => item.id), ['8', '7', '6', '5', '4']);
  assert.equal(history.length, 9); assert.equal(history[0].id, '0');
});
test('full history retains conversations beyond the sidebar limit and the previous fifty-chat limit', () => {
  let history: CareConversation[] = [];
  for (let i = 0; i < 60; i++) history = saveConversation(history, { ...entry, id: String(i) });
  assert.equal(history.length, 60);
  assert.equal(readHistory({ getItem: () => JSON.stringify(history) }).length, 60);
  assert.equal(recentConversations(history).length, 5);
});
test('saved conversations survive serialization and renamed titles survive later replies', () => {
  const history = saveConversation([{ ...entry, title: 'My title', customTitle: 'My title' }], { ...entry, messages: [...entry.messages, { role: 'user', content: 'A test' }] });
  assert.equal(history.length, 1); assert.equal(history[0].title, 'My title');
  const restored = readHistory({ getItem: key => key === HISTORY_KEY ? JSON.stringify(history) : null });
  assert.deepEqual(restored, history);
  assert.equal(saveConversation(restored, { ...entry, id: 'two' })[0].id, 'two');
});
test('broken, blocked or malformed browser storage cannot break startup', () => {
  for (const raw of ['bad JSON', '{}', '[null]', JSON.stringify([{ ...entry, result: {} }]), JSON.stringify([{ ...entry, messages: [{}] }])]) {
    assert.deepEqual(readHistory({ getItem: () => raw }), []);
  }
  assert.deepEqual(readHistory({ getItem: () => { throw new Error('blocked'); } }), []);
});
test('continuing after a recommendation preserves context and caps backend history at 40 turns', () => {
  const messages: Message[] = Array.from({ length: 44 }, (_, i) => ({ role: i % 2 ? 'assistant' : 'user', content: `turn ${i}` }));
  messages[43].kind = 'recommendation';
  const request = requestHistory(messages);
  assert.equal(request.length, 40); assert.equal(request[0].content, 'turn 4');
  assert.equal(request.at(-1)?.kind, 'recommendation'); assert.equal(messages.length, 44);
});
