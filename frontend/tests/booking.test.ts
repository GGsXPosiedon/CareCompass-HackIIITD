import test from 'node:test';
import assert from 'node:assert/strict';
import { bookingDate, bookingSlots } from '../src/lib/flow.ts';
import { ApiError, createJsonRequest } from '../src/lib/http.ts';

test('booking dates follow India midnight regardless of the browser timezone', () => {
  const now = new Date('2026-10-24T19:00:00Z');
  assert.equal(bookingDate(0, now), '2026-10-25');
  assert.equal(bookingDate(1, now), '2026-10-26');
  assert.equal(bookingDate(1, new Date('2026-12-31T20:00:00Z')), '2027-01-02');
});

test('late-day bookings reject past times today but allow the next day', () => {
  const now = new Date('2026-10-24T20:30:00+05:30');
  const slots = ['07:00', '08:00', '18:00'];
  assert.deepEqual(bookingSlots(slots, '2026-10-24', now), []);
  assert.deepEqual(bookingSlots(slots, '2026-10-25', now), slots);
});

test('booking slots exclude the current minute and sort and deduplicate remaining times', () => {
  assert.deepEqual(bookingSlots(['14:00', '12:00', '13:00', '13:00'], '2026-10-24', new Date('2026-10-24T12:00:59+05:30')), ['13:00', '14:00']);
});

test('API transport preserves the selected date and booking payload', async () => {
  const calls: { url: string; method?: string; body?: unknown }[] = [];
  const request = createJsonRequest('/api/', (async (url, init) => {
    calls.push({ url: String(url), method: init?.method, body: init?.body });
    return Response.json({ id: 'BK-1' });
  }) as typeof fetch);
  await request('/caregivers?ids=SYN_006&date=2026-10-25');
  const payload = { caregiver_id: 'SYN_006', date: '2026-10-25', slot: '07:00' };
  await request('/bookings', payload);
  assert.equal(calls[0].url, '/api/caregivers?ids=SYN_006&date=2026-10-25');
  assert.equal(calls[0].method, 'GET');
  assert.deepEqual(JSON.parse(String(calls[1].body)), payload);
  assert.equal(calls[1].method, 'POST');
});

test('booking conflicts retain HTTP 409 so the UI can refresh instead of retrying blindly', async () => {
  const request = createJsonRequest('/api', (async () => new Response('', { status: 409 })) as typeof fetch);
  await assert.rejects(request('/bookings', {}), error => error instanceof ApiError && error.status === 409);
});

test('API outages are surfaced and never replaced with a successful demo response', async () => {
  const unavailable = createJsonRequest('/api', (async () => new Response('', { status: 502 })) as typeof fetch);
  await assert.rejects(unavailable('/triage', { user_input: 'unseen request' }), error => error instanceof ApiError && error.status === 502);
  const disconnected = createJsonRequest('/api', (async () => { throw new TypeError('Failed to fetch'); }) as typeof fetch);
  await assert.rejects(disconnected('/bookings', {}), TypeError);
});
