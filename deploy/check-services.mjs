import assert from 'node:assert/strict';

// Run against `vercel dev --local` or a deployed URL. No paid AI calls or reservations.
const base = new URL(process.argv[2] || 'http://127.0.0.1:3000');
const get = path => fetch(new URL(path, base), { signal: AbortSignal.timeout(20000) });
function expectApi(response, path, status) {
  assert.ok(response.headers.get('content-type')?.includes('application/json'),
    `${path}: expected API JSON, received HTTP ${response.status}. Check Vercel Root Directory is the repository root, deploy both services using vercel.json, and redeploy. Static frontend output alone does not include API functions.`);
  assert.equal(response.status, status, path);
  assert.equal(response.headers.get('cache-control'), 'no-store', path);
  if (path !== '/api/voice') assert.ok(response.headers.get('x-request-id'), `${path}: missing application request ID`);
}
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
  expectApi(response, path, 200);
  await response.json();
}
for (const [path, status] of [['/api/triage', 405], ['/api/triage/trace', 404], ['/api/care', 404]]) {
  const response = await get(path);
  expectApi(response, path, status);
  assert.ok((await response.json()).error, 'Expected the frontend proxy, not the old Vite API proxy');
}
const invalid = await fetch(new URL('/api/triage', base), {
  method: 'POST', headers: { 'Content-Type': 'application/json', Origin: base.origin },
  body: JSON.stringify({ user_input: '' }), signal: AbortSignal.timeout(20000),
});
expectApi(invalid, '/api/triage', 422);
assert.ok(Array.isArray((await invalid.json()).detail));
console.log('Services check passed: pages, install assets, voice, runtime care binding, POST validation and private diagnostics.');
