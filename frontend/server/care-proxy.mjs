const routes = new Map([
  ['/api/triage', 'POST'], ['/api/caregivers', 'GET'],
  ['/api/bookings', 'POST'], ['/api/health', 'GET'],
]);
const json = (error, status) => Response.json({ error }, { status, headers: { 'Cache-Control': 'no-store' } });

export async function handleCare(request, env = process.env, fetcher = fetch) {
  const incoming = new URL(request.url);
  const method = routes.get(incoming.pathname);
  if (!method) return json('NOT_FOUND', 404);
  if (request.method !== method) return json('METHOD_NOT_ALLOWED', 405);
  const origin = request.headers.get('origin');
  if (origin && origin !== incoming.origin) return json('ORIGIN_REFUSED', 403);
  if (!env.BACKEND_URL) return json('BACKEND_BINDING_UNAVAILABLE', 503);
  try {
    // Bindings exist only in functions at runtime. Preserve any base-path in the injected URL.
    const target = new URL(incoming.pathname.slice('/api/'.length), `${env.BACKEND_URL.replace(/\/$/, '')}/`);
    target.search = incoming.search;
    const body = method === 'POST' ? await request.arrayBuffer() : undefined;
    if (body && body.byteLength > 256 * 1024) return json('REQUEST_TOO_LARGE', 413);
    const response = await fetcher(target, {
      method, headers: { 'Content-Type': 'application/json' }, body,
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(44000)]),
      redirect: 'error',
    });
    // Preserve API status codes (especially booking conflicts), but never upstream cookies/cache headers.
    return new Response(response.body, { status: response.status, headers: {
      'Content-Type': response.headers.get('content-type') || 'application/json',
      'Cache-Control': 'no-store',
    } });
  } catch (error) {
    return json(error?.name === 'TimeoutError' ? 'BACKEND_TIMEOUT' : 'BACKEND_UNAVAILABLE', error?.name === 'TimeoutError' ? 504 : 502);
  }
}
