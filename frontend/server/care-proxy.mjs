import { randomUUID } from 'node:crypto';

const routes = new Map([
  ['/api/triage', 'POST'], ['/api/caregivers', 'GET'],
  ['/api/bookings', 'POST'], ['/api/health', 'GET'],
]);
const json = (error, status) => Response.json({ error }, { status, headers: { 'Cache-Control': 'no-store' } });

export async function handleCare(request, env = process.env, fetcher = fetch) {
  const incoming = new URL(request.url);
  const requestId = randomUUID();
  const started = performance.now();
  const finish = (response, code, errorType) => {
    response.headers.set('X-Request-ID', requestId);
    const entry = JSON.stringify({ event: 'care_proxy_request', request_id: requestId,
      method: request.method, path: incoming.pathname, status: response.status,
      duration_ms: Math.round(performance.now() - started), code, error_type: errorType });
    if (response.status >= 500) console.error(entry);
    else if (response.status >= 400) console.warn(entry);
    else console.info(entry);
    return response;
  };
  const fail = (code, status, errorType) => finish(json(code, status), code, errorType);
  const method = routes.get(incoming.pathname);
  if (!method) return fail('NOT_FOUND', 404);
  if (request.method !== method) return fail('METHOD_NOT_ALLOWED', 405);
  const origin = request.headers.get('origin');
  if (origin && origin !== incoming.origin) return fail('ORIGIN_REFUSED', 403);
  if (!env.BACKEND_URL) return fail('BACKEND_BINDING_UNAVAILABLE', 503);
  try {
    // Bindings exist only in functions at runtime. Preserve any base-path in the injected URL.
    const target = new URL(incoming.pathname.slice('/api/'.length), `${env.BACKEND_URL.replace(/\/$/, '')}/`);
    target.search = incoming.search;
    const body = method === 'POST' ? await request.arrayBuffer() : undefined;
    if (body && body.byteLength > 256 * 1024) return fail('REQUEST_TOO_LARGE', 413);
    const response = await fetcher(target, {
      method, headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId }, body,
      signal: AbortSignal.any([request.signal, AbortSignal.timeout(44000)]),
      redirect: 'error',
    });
    if (!response.headers.get('content-type')?.includes('application/json')) {
      await response.body?.cancel();
      return fail('INVALID_BACKEND_RESPONSE', 502);
    }
    // Preserve API status codes (especially booking conflicts), but never upstream cookies/cache headers.
    return finish(new Response(response.body, { status: response.status, headers: {
      'Content-Type': response.headers.get('content-type') || 'application/json',
      'Cache-Control': 'no-store',
    } }), response.ok ? undefined : 'BACKEND_HTTP_ERROR');
  } catch (error) {
    return fail(error?.name === 'TimeoutError' ? 'BACKEND_TIMEOUT' : 'BACKEND_UNAVAILABLE', error?.name === 'TimeoutError' ? 504 : 502, error?.name);
  }
}
