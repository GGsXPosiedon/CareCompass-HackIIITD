import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import gateway from '../server/gateway.mjs';

test('the deployed Node gateway serves voice and forwards care requests through the backend binding', async () => {
  const previousBinding = process.env.BACKEND_URL;
  const previousFetch = globalThis.fetch;
  try {
    process.env.BACKEND_URL = 'https://private.example/backend/';
    globalThis.fetch = async (url, init) => {
      assert.equal(String(url), 'https://private.example/backend/triage');
      assert.equal(init?.method, 'POST');
      assert.deepEqual(JSON.parse(new TextDecoder().decode(init?.body as ArrayBuffer)), { user_input: 'hi' });
      assert.ok(new Headers(init?.headers).get('x-request-id'));
      return Response.json({ follow_up_question: 'How can I help?' });
    };
    const response = await gateway.fetch(new Request('https://care.example/api/triage', {
      method: 'POST', headers: { origin: 'https://care.example', 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_input: 'hi' }),
    }));
    assert.equal(response.status, 200);
    assert.equal((await response.json()).follow_up_question, 'How can I help?');
    assert.ok(response.headers.get('x-request-id'));
    const voice = await gateway.fetch(new Request('https://care.example/api/voice'));
    assert.equal(voice.status, 200);
    assert.ok(['sarvam', 'browser'].includes((await voice.json()).provider));
    assert.equal((await gateway.fetch(new Request('https://care.example/api/triage'))).status, 405);
    assert.equal((await gateway.fetch(new Request('https://care.example/api/triage/trace'))).status, 404);
  } finally {
    globalThis.fetch = previousFetch;
    if (previousBinding === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = previousBinding;
  }
});

test('production API routing targets an explicit Node service rather than static Vite output', () => {
  const config = JSON.parse(readFileSync(new URL('../../vercel.json', import.meta.url), 'utf8'));
  const route = config.rewrites.find((item: { source: string }) => item.source === '/api/(.*)');
  const service = config.services[route.destination.service];
  assert.equal(service.framework, 'node');
  assert.equal(service.entrypoint, 'server/gateway.mjs');
  assert.ok(service.bindings.some((binding: { env: string; service: string }) => binding.env === 'BACKEND_URL' && binding.service === 'backend'));
  assert.ok(!config.services.frontend.functions);
});
