import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, createJsonRequest } from '../src/lib/http.ts';

test('missing deployed functions produce an actionable error without leaking bodies or query values', async () => {
  const logs: unknown[] = [];
  const original = console.error;
  console.error = (...args) => logs.push(args);
  try {
    const request = createJsonRequest('/api', (async () => new Response('NOT_FOUND private upstream text', { status: 404 })) as typeof fetch);
    await assert.rejects(request('/triage?secret=value', { user_input: 'private patient text' }), error =>
      error instanceof ApiError && error.status === 404 && error.code === 'API_ROUTE_NOT_FOUND');
    const log = JSON.stringify(logs);
    assert.ok(log.includes('API_ROUTE_NOT_FOUND'));
    for (const secret of ['private', 'secret', 'value']) assert.ok(!log.includes(secret));
  } finally { console.error = original; }
});

test('backend error codes and request IDs survive the HTTP transport', async () => {
  const request = createJsonRequest('/api', (async () => Response.json({ error: 'BACKEND_BINDING_UNAVAILABLE' }, {
    status: 503, headers: { 'X-Request-ID': 'test-reference' },
  })) as typeof fetch);
  await assert.rejects(request('/triage', {}), error => error instanceof ApiError &&
    error.code === 'BACKEND_BINDING_UNAVAILABLE' && error.requestId === 'test-reference');
});

test('HTML and malformed JSON cannot masquerade as successful care responses', async () => {
  for (const response of [new Response('<html>SPA fallback</html>'), new Response('{broken', { headers: { 'Content-Type': 'application/json' } })]) {
    const request = createJsonRequest('/api', (async () => response) as typeof fetch);
    await assert.rejects(request('/triage', {}), error => error instanceof ApiError && error.code === 'INVALID_API_RESPONSE');
  }
});
