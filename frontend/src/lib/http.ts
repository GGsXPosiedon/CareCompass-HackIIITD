export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  constructor(status: number, code = 'API_REQUEST_FAILED', requestId: string | null = null) {
    super(`${code}_${status}`); this.status = status; this.code = code; this.requestId = requestId;
  }
}

export function createJsonRequest(base: string, fetcher: typeof fetch = fetch) {
  return async (path: string, body?: unknown, signal?: AbortSignal): Promise<unknown> => {
    const started = performance.now();
    let status = 0;
    let requestId: string | null = null;
    try {
      const response = await fetcher(`${base.replace(/\/$/, '')}${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(45000)]) : AbortSignal.timeout(45000),
      });
      status = response.status;
      requestId = response.headers.get('x-request-id');
      if (!response.ok) {
        // Never log or surface upstream bodies: validation errors can contain patient input.
        const data = await response.json().catch(() => null);
        const code = typeof data?.error === 'string' && /^[A-Z_]{1,64}$/.test(data.error) ? data.error : status === 404 ? 'API_ROUTE_NOT_FOUND' : 'API_REQUEST_FAILED';
        throw new ApiError(status, code, requestId);
      }
      if (!response.headers.get('content-type')?.includes('application/json')) throw new ApiError(status, 'INVALID_API_RESPONSE', requestId);
      try { return await response.json(); }
      catch { throw new ApiError(status, 'INVALID_API_RESPONSE', requestId); }
    } catch (error) {
      if (!signal?.aborted) console.error('carecompass.api', {
        event: 'request_failed', path: path.split('?')[0], method: body === undefined ? 'GET' : 'POST',
        status, request_id: requestId, duration_ms: Math.round(performance.now() - started),
        code: error instanceof ApiError ? error.code : error instanceof Error ? error.name : 'UNKNOWN_ERROR',
      });
      throw error;
    }
  };
}
