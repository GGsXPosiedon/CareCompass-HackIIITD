import assert from 'node:assert/strict';

// Run after `vercel dev --local`. Makes no paid AI calls or reservations.
const base = new URL(process.argv[2] || 'http://127.0.0.1:3000');
const get = path => fetch(new URL(path, base), { signal: AbortSignal.timeout(20000) });
for (const path of ['/', '/care', '/bookings', '/settings', '/chat/test-conversation']) {
  const response = await get(path);
  assert.equal(response.status, 200, path);
  assert.ok((await response.text()).includes('id="root"'), path);
}
assert.equal((await (await get('/manifest.webmanifest')).json()).display, 'standalone');
const png = Buffer.from(await (await get('/icons/icon-192.png')).arrayBuffer());
assert.equal(png.toString('hex', 0, 8), '89504e470d0a1a0a');
for (const path of ['/api/voice', '/api/health', '/api/caregivers?ids=CG_001']) {
  const response = await get(path);
  assert.equal(response.status, 200, path);
  assert.equal(response.headers.get('cache-control'), 'no-store', path);
  await response.json();
}
for (const [path, status] of [['/api/triage', 405], ['/api/triage/trace', 404], ['/api/care', 404]]) {
  const response = await get(path);
  assert.equal(response.status, status, path);
  assert.ok((await response.json()).error, 'Expected the frontend proxy, not the old Vite API proxy');
}
const invalid = await fetch(new URL('/api/triage', base), {
  method: 'POST', headers: { 'Content-Type': 'application/json', Origin: base.origin },
  body: JSON.stringify({ user_input: '' }), signal: AbortSignal.timeout(20000),
});
assert.equal(invalid.status, 422);
assert.ok(Array.isArray((await invalid.json()).detail));
console.log('Services check passed: pages, install assets, voice, runtime care binding, POST validation and private diagnostics.');
