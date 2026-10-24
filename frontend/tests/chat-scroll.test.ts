import assert from 'node:assert/strict';
import { test } from 'node:test';
import { isNearBottom } from '../src/lib/chat-scroll.ts';
import { createJsonRequest } from '../src/lib/http.ts';

test('short chats follow new messages, while reading older messages pauses following', () => {
  assert.equal(isNearBottom({ scrollTop: 0, scrollHeight: 200, clientHeight: 600 }), true);
  assert.equal(isNearBottom({ scrollTop: 930, scrollHeight: 1600, clientHeight: 600 }), true);
  assert.equal(isNearBottom({ scrollTop: 300, scrollHeight: 1600, clientHeight: 600 }), false);
  assert.equal(isNearBottom({ scrollTop: -20, scrollHeight: 1600, clientHeight: 600 }), false);
  assert.equal(isNearBottom({ scrollTop: 1000, scrollHeight: 1600, clientHeight: 600 }), true);
});

test('stopping an in-flight chat aborts the actual HTTP request', async () => {
  const controller = new AbortController();
  let requestSignal: AbortSignal | null = null;
  const request = createJsonRequest('/api', async (_url, options) => {
    requestSignal = options?.signal as AbortSignal;
    return new Promise<Response>((_resolve, reject) => {
      requestSignal!.addEventListener('abort', () => reject(requestSignal!.reason), { once: true });
    });
  });
  const pending = request('/triage', { user_input: 'Hello' }, controller.signal);
  controller.abort(new DOMException('Stopped', 'AbortError'));
  await assert.rejects(pending, { name: 'AbortError' });
  assert.equal((requestSignal as AbortSignal | null)?.aborted, true);
});
