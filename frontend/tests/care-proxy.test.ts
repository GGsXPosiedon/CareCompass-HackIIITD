import assert from 'node:assert/strict';
import { test } from 'node:test';
import { handleCare } from '../server/care-proxy.mjs';

const env = { BACKEND_URL: 'https://internal.example/service/backend/' };
const request = (path: string, body?: unknown) => new Request(`https://care.example${path}`, {
  method: body === undefined ? 'GET' : 'POST',
  headers: { origin: 'https://care.example', 'Content-Type': 'application/json', cookie: 'private=do-not-forward' },
  ...(body === undefined ? {} : { body: JSON.stringify(body) }),
});

test('care proxy maps the original public path to the bound backend and forwards the request body', async () => {
  const payload = { user_input: 'Need a blood test', conversation_history: [] };
  const response = await handleCare(request('/api/triage', payload), env, async (url, init) => {
    assert.equal(String(url), 'https://internal.example/service/backend/triage');
    assert.equal(init.method, 'POST');
    assert.deepEqual(JSON.parse(new TextDecoder().decode(init.body)), payload);
    assert.equal(init.headers.cookie, undefined);
    assert.ok(init.signal instanceof AbortSignal);
    assert.equal(init.redirect, 'error');
    return Response.json({ follow_up_question: 'Which test?' });
  });
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('cache-control'), 'no-store');
});

test('care proxy preserves caregiver queries and booking conflicts', async () => {
  const query = '/api/caregivers?ids=CG_001%2CCG_002&date=2026-10-25';
  await handleCare(request(query), env, async (url, init) => {
    assert.equal(new URL(url).search, new URL(`https://care.example${query}`).search);
    assert.equal(init.method, 'GET'); assert.equal(init.body, undefined);
    return Response.json([]);
  });
  const response = await handleCare(request('/api/bookings', { slot: '10:00' }), env,
    async () => Response.json({ detail: 'slot already booked' }, { status: 409, headers: { 'set-cookie': 'upstream=private' } }));
  assert.equal(response.status, 409);
  assert.deepEqual(await response.json(), { detail: 'slot already booked' });
  assert.equal(response.headers.get('set-cookie'), null);
});

test('care proxy fails closed without a binding and rejects routes, methods and origins before forwarding', async () => {
  const never = async () => { throw new Error('must not call backend'); };
  assert.equal((await handleCare(request('/api/health'), {}, never)).status, 503);
  for (const path of ['/api/voice', '/api/care', '/api/triage/trace', '/api/v1/graph']) {
    assert.equal((await handleCare(request(path), env, never)).status, 404);
  }
  assert.equal((await handleCare(request('/api/triage'), env, never)).status, 405);
  const crossOrigin = request('/api/bookings', {});
  crossOrigin.headers.set('origin', 'https://other.example');
  assert.equal((await handleCare(crossOrigin, env, never)).status, 403);
  assert.equal((await handleCare(request('/api/triage', { user_input: 'x'.repeat(256 * 1024) }), env, never)).status, 413);
});

test('care proxy sanitizes connection errors and timeouts without leaking the binding URL', async () => {
  for (const [name, status] of [['TypeError', 502], ['TimeoutError', 504]] as const) {
    const response = await handleCare(request('/api/health'), env, async () => {
      throw new DOMException(`private failure at ${env.BACKEND_URL}`, name);
    });
    assert.equal(response.status, status);
    assert.ok(!(await response.text()).includes(env.BACKEND_URL));
  }
});

test('care proxy correlates backend and client diagnostics without logging patient input or query values', async () => {
  const entries: string[] = [];
  const original = console.info;
  console.info = entry => entries.push(entry);
  try {
    let forwardedId: string | undefined;
    const response = await handleCare(request('/api/triage?private=secret', { user_input: 'patient-private-text' }), env, async (_, init) => {
      forwardedId = init.headers['X-Request-ID'];
      return Response.json({ follow_up_question: 'Hello' });
    });
    assert.ok(forwardedId);
    assert.equal(response.headers.get('x-request-id'), forwardedId);
    const row = JSON.parse(entries[0]);
    assert.equal(row.request_id, forwardedId);
    assert.equal(row.status, 200);
    assert.equal(row.path, '/api/triage');
    assert.equal(typeof row.duration_ms, 'number');
    assert.ok(!entries.join('').includes('patient-private-text'));
    assert.ok(!entries.join('').includes('secret'));
    assert.ok(!entries.join('').includes(env.BACKEND_URL));
  } finally { console.info = original; }
});

test('care proxy reports a non-JSON backend response as a gateway failure', async () => {
  const response = await handleCare(request('/api/health'), env, async () => new Response('<html>private error</html>'));
  assert.equal(response.status, 502);
  assert.deepEqual(await response.json(), { error: 'INVALID_BACKEND_RESPONSE' });
  assert.ok(response.headers.get('x-request-id'));
});
