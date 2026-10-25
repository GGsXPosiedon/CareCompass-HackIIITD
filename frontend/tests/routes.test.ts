import assert from 'node:assert/strict';
import { test } from 'node:test';
import { conversationPath, pagePaths, parentPath, resolveRoute } from '../src/lib/routes.ts';

test('each sidebar page has a distinct route and supports direct loads', () => {
  assert.equal(new Set(Object.values(pagePaths)).size, 6);
  for (const [page, path] of Object.entries(pagePaths)) {
    assert.equal(resolveRoute(path).page, page);
    assert.equal(resolveRoute(`${path}/`).page, page);
  }
  assert.equal(resolveRoute('/').page, 'care');
});
test('saved chat links round-trip IDs and unknown URLs have a missing-page state', () => {
  assert.deepEqual(resolveRoute(conversationPath('chat with spaces')), { page: 'care', conversationId: 'chat with spaces' });
  for (const path of ['/missing', '/profile', '/profile/unknown', '/chat', '/chat/%ZZ']) assert.equal(resolveRoute(path).page, 'not-found');
});
test('Back has a safe in-app destination for direct page loads', () => {
  assert.equal(parentPath('/services'), '/bookings');
  assert.equal(parentPath('/settings'), '/care');
  assert.equal(parentPath('/history', 'one'), '/chat/one');
});
